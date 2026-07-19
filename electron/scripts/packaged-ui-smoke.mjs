import assert from "node:assert/strict";
import { mkdir, stat } from "node:fs/promises";

const port = Number(process.argv[2] || 9223);
const outputDir = process.argv[3];
assert(outputDir, "Usage: node scripts/packaged-ui-smoke.mjs <debug-port> <output-dir>");
await mkdir(outputDir, { recursive: true });

const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function findPage() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then((response) => response.json());
      const page = targets.find((target) => target.type === "page" && target.webSocketDebuggerUrl);
      if (page) return page;
    } catch {
      // Electron may still be starting.
    }
    await delay(500);
  }
  throw new Error("Electron did not expose a debuggable renderer");
}

const page = await findPage();
const socket = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

let sequence = 0;
const pending = new Map();
socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});

function command(method, params = {}) {
  sequence += 1;
  const id = sequence;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

async function evaluate(expression) {
  const response = await command("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true
  });
  if (response.exceptionDetails) {
    throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
  }
  return response.result.value;
}

async function waitFor(expression, timeoutMilliseconds = 120000) {
  const deadline = Date.now() + timeoutMilliseconds;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await delay(500);
  }
  throw new Error(`Timed out waiting for: ${expression}`);
}

const clickButton = (label) => evaluate(`(() => {
  const button = [...document.querySelectorAll('button')].find((item) => item.textContent.trim() === ${JSON.stringify(label)});
  if (!button || button.disabled) return false;
  button.click();
  return true;
})()`);

await command("Runtime.enable");
await waitFor("Boolean(document.querySelector('#media-url'))", 30000);

const navigation = await evaluate("[...document.querySelectorAll('nav button')].map((button) => button.textContent.trim())");
assert.deepEqual(navigation.slice(0, 5), ["Nueva descarga", "Cola", "Historial", "Ajustes", "Acerca de"]);

assert.equal(await clickButton("Cola"), true);
await waitFor("document.querySelector('h1')?.textContent === 'Cola'");
assert.equal(await clickButton("Historial"), true);
await waitFor("document.querySelector('h1')?.textContent === 'Historial'");
assert.equal(await clickButton("Ajustes"), true);
await waitFor("document.querySelector('h1')?.textContent === 'Ajustes'");

await evaluate(`(() => {
  const select = document.querySelectorAll('.settings-grid select')[1];
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
  setter.call(select, 'none');
  select.dispatchEvent(new Event('change', { bubbles: true }));
})()`);
assert.equal(await clickButton("Guardar cambios"), true);

const configuredOutput = await evaluate("window.drDownload.getConfig().then(config => config.output_dir)");
assert.equal(configuredOutput, outputDir);
assert.equal(await clickButton("Nueva descarga"), true);
await waitFor("Boolean(document.querySelector('#media-url'))", 30000);

await evaluate(`(() => {
  const input = document.querySelector('#media-url');
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(input, 'https://youtu.be/eOX5BdEGfMk');
  input.dispatchEvent(new Event('input', { bubbles: true }));
})()`);
await waitFor("!document.querySelector('#media-url').disabled");
assert.equal(await clickButton("Analizar enlace"), true);
await waitFor("document.body.innerText.includes('Rammstein - Wilder Wein Instrumental Cover')", 120000);

const tasks = [];
for (const formatId of ["audio-mp3", "video-best"]) {
  await evaluate(`(() => {
    const select = document.querySelector('.media-controls select');
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
    setter.call(select, ${JSON.stringify(formatId)});
    select.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  const existingIds = await evaluate("window.drDownload.listDownloads().then(items => items.map(item => item.id))");
  assert.equal(await clickButton("Agregar a la cola"), true);

  const task = await evaluate(`(async () => {
    const known = new Set(${JSON.stringify(existingIds)});
    for (let attempt = 0; attempt < 600; attempt += 1) {
      const items = await window.drDownload.listDownloads();
      const item = items.find((candidate) => !known.has(candidate.id));
      if (item && ['completed', 'failed', 'cancelled'].includes(item.status)) return item;
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    throw new Error('Download did not reach a terminal state');
  })()`);

  assert.equal(task.status, "completed", JSON.stringify(task.error));
  assert.equal(task.progress, 100);
  assert(task.filename, "Completed task did not report a final filename");
  assert((await stat(task.filename)).size > 0, "Completed file is empty");
  tasks.push({ id: task.id, formatId, status: task.status, progress: task.progress, filename: task.filename });

  if (formatId === "audio-mp3") {
    assert.equal(await clickButton("Nueva descarga"), true);
    await waitFor("Boolean(document.querySelector('#media-url'))", 30000);
    await evaluate(`(() => {
      const input = document.querySelector('#media-url');
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(input, 'https://youtu.be/eOX5BdEGfMk');
      input.dispatchEvent(new Event('input', { bubbles: true }));
    })()`);
    assert.equal(await clickButton("Analizar enlace"), true);
    await waitFor("document.body.innerText.includes('Rammstein - Wilder Wein Instrumental Cover')", 120000);
  }
}

console.log(JSON.stringify({
  navigation,
  inspected: true,
  tasks
}, null, 2));
socket.close();
