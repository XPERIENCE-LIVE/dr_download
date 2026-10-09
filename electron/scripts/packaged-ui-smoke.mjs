import assert from "node:assert/strict";
import { mkdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";

const port = Number(process.argv[2] || 9223);
const outputDir = process.argv[3];
const artifactDir = process.argv[4] || path.dirname(outputDir || ".");
assert(outputDir, "Usage: node scripts/packaged-ui-smoke.mjs <debug-port> <output-dir>");
await mkdir(outputDir, { recursive: true });

const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function findPage() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const targets = await fetch(`http://127.0.0.1:${port}/json/list`, { signal: AbortSignal.timeout(2000) }).then((response) => response.json());
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
socket.addEventListener("close", () => {
  for (const { reject } of pending.values()) reject(new Error("Electron debugger disconnected"));
  pending.clear();
});

function command(method, params = {}, timeoutMilliseconds = 30000) {
  sequence += 1;
  const id = sequence;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Debugger command timed out: ${method}`));
    }, timeoutMilliseconds);
    pending.set(id, {
      resolve: (result) => { clearTimeout(timer); resolve(result); },
      reject: (reason) => { clearTimeout(timer); reject(reason); }
    });
  });
}

async function evaluate(expression, timeoutMilliseconds = 30000) {
  const response = await command("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true
  }, timeoutMilliseconds);
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
  const button = [...document.querySelectorAll('button')].find((item) => item.getClientRects().length && (item.textContent.trim() === ${JSON.stringify(label)} || item.querySelector('span')?.textContent.trim() === ${JSON.stringify(label)}));
  if (!button || button.disabled) return false;
  button.click();
  return true;
})()`);

async function setValue(selector, value) {
  assert.equal(await evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element || element.disabled) return false;
    const prototype = element.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, ${JSON.stringify(value)});
    element.dispatchEvent(new Event(element.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
    return true;
  })()`), true, `Unavailable input: ${selector}`);
}

async function screenshot(name) {
  const result = await command("Page.captureScreenshot", { format: "png" });
  await writeFile(path.join(artifactDir, name), Buffer.from(result.data, "base64"));
}

await command("Runtime.enable");
await waitFor("Boolean(document.querySelector('#media-url'))", 30000);

const navigation = await evaluate("[...document.querySelectorAll('nav button')].map((button) => button.textContent.trim())");
assert.deepEqual(navigation.slice(0, 5), ["Nueva descarga", "Cola", "Historial", "Ajustes", "Acerca de"]);
await waitFor("document.querySelector('.engine-ready')?.textContent.includes('MOTOR LOCAL LISTO')", 30000);
const configuredOutput = await evaluate("window.drDownload.getConfig().then(config => config.output_dir)");
assert.equal(configuredOutput, outputDir, "Backend configuration is not isolated; refusing to change settings or download");
assert.equal(await evaluate("window.drDownload.getConfig().then(config => config.cookie_source)"), "none");
const initialTasks = await evaluate("window.drDownload.listDownloads().then(items => items.map(item => item.id))");
const invalidPathError = await evaluate(`(async () => {
  try {
    await window.drDownload.createDownload({
      url: 'https://example.com/bridge-check', format_id: 'video-compatible',
      output_dir: 'relative-smoke-path', cookie_source: 'none'
    });
    return null;
  } catch (reason) {
    return { message: reason.message, detail: reason.detail };
  }
})()`);
assert.equal(invalidPathError?.detail?.error_code, "invalid_path", "Real IPC bridge lost the structured directory rejection");
assert(invalidPathError.detail.recovery, "Real IPC bridge lost the recovery guidance");
assert.deepEqual(await evaluate("window.drDownload.listDownloads().then(items => items.map(item => item.id))"), initialTasks, "Invalid path queued a download");
await screenshot("new-download-es.png");
const mediaUrl = "https://youtu.be/eOX5BdEGfMk";
await setValue("#media-url", mediaUrl);

assert.equal(await clickButton("Cola"), true);
await waitFor("[...document.querySelectorAll('h1')].find(item => item.getClientRects().length)?.textContent === 'Cola'");
assert.equal(await clickButton("Historial"), true);
await waitFor("[...document.querySelectorAll('h1')].find(item => item.getClientRects().length)?.textContent === 'Historial'");
assert.equal(await clickButton("Ajustes"), true);
await waitFor("[...document.querySelectorAll('h1')].find(item => item.getClientRects().length)?.textContent === 'Ajustes'");
await setValue(".settings-grid select", "en");
await waitFor("[...document.querySelectorAll('h1')].find(item => item.getClientRects().length)?.textContent === 'Settings'");
const englishNavigation = await evaluate("[...document.querySelectorAll('nav button span')].map((item) => item.textContent.trim())");
assert.deepEqual(englishNavigation, ["New download", "Queue", "History", "Settings", "About"]);
assert.equal(await clickButton("Save changes"), true);
await waitFor("window.drDownload.getConfig().then(config => config.language === 'en')", 10000);
await waitFor("document.body.innerText.includes('Changes saved')", 10000);
assert.equal(await clickButton("About"), true);
await waitFor("[...document.querySelectorAll('h1')].find(item => item.getClientRects().length)?.textContent === 'About'");
assert.equal(await clickButton("New download"), true);
await waitFor("Boolean(document.querySelector('#media-url'))", 30000);
assert.equal(await evaluate("document.querySelector('#media-url').value"), mediaUrl, "URL draft was lost while navigating");
assert.equal(await evaluate("document.querySelector('label[for=media-url]').textContent"), "Video link");
assert.equal(await clickButton("Inspect link"), true);
await waitFor("document.body.innerText.includes('Rammstein - Wilder Wein Instrumental Cover')", 120000);
const presets = await evaluate("[...document.querySelector('.media-controls select').options].map(option => option.value)");
assert.deepEqual(presets, ["video-compatible", "video-best", "audio-mp3"]);
assert.equal(await evaluate("document.querySelector('.advanced-control').textContent.trim()"), "Advanced formats");
await evaluate("document.querySelector('.advanced-control input').click()");
await waitFor("document.querySelector('.media-controls select').options.length > 3", 10000);
await evaluate("document.querySelector('.advanced-control input').click()");
await waitFor("document.querySelector('.media-controls select').options.length === 3", 10000);
await setValue(".media-controls select", "audio-mp3");
assert.equal(await clickButton("Queue"), true);
await waitFor("[...document.querySelectorAll('h1')].find(item => item.getClientRects().length)?.textContent === 'Queue'");
assert.equal(await clickButton("New download"), true);
await waitFor("Boolean(document.querySelector('.media-controls select'))", 10000);
assert.equal(await evaluate("document.querySelector('#media-url').value"), mediaUrl);
assert.equal(await evaluate("document.querySelector('.media-controls select').value"), "audio-mp3");
assert(await evaluate("document.body.innerText.includes('Rammstein - Wilder Wein Instrumental Cover')"), "Analyzed media draft was lost");
await screenshot("new-download-en.png");
assert.equal(await clickButton("Settings"), true);
await waitFor("[...document.querySelectorAll('h1')].find(item => item.getClientRects().length)?.textContent === 'Settings'");
await setValue(".settings-grid select", "es");
assert.equal(await clickButton("Guardar cambios"), true);
await waitFor("window.drDownload.getConfig().then(config => config.language === 'es')", 10000);
await waitFor("document.body.innerText.includes('Cambios guardados')", 10000);

assert.equal(await clickButton("Nueva descarga"), true);
await waitFor("Boolean(document.querySelector('#media-url'))", 30000);

await waitFor("Boolean(document.querySelector('.media-controls select'))", 10000);

const tasks = [];
for (const formatId of ["audio-mp3", "video-best", "video-compatible"]) {
  await setValue(".media-controls select", formatId);
  const existingIds = await evaluate("window.drDownload.listDownloads().then(items => items.map(item => item.id))");
  assert.equal(await clickButton("Agregar a la cola"), true);
  await waitFor(`window.drDownload.listDownloads().then(items => items.some(item => !${JSON.stringify(existingIds)}.includes(item.id)))`, 30000);
  await waitFor("[...document.querySelectorAll('button')].some(button => button.textContent.trim() === 'Ver cola')", 10000);
  assert.equal(await clickButton("Ver cola"), true);
  await waitFor("[...document.querySelectorAll('h1')].find(item => item.getClientRects().length)?.textContent === 'Cola'", 10000);

  const task = await evaluate(`(async () => {
    const known = new Set(${JSON.stringify(existingIds)});
    for (let attempt = 0; attempt < 600; attempt += 1) {
      const items = await window.drDownload.listDownloads();
      const item = items.find((candidate) => !known.has(candidate.id));
      if (item && ['completed', 'failed', 'cancelled'].includes(item.status)) return item;
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    throw new Error('Download did not reach a terminal state');
  })()`, 650000);

  assert.equal(task.status, "completed", JSON.stringify(task.error));
  assert.equal(task.progress, 100);
  assert(task.filename, "Completed task did not report a final filename");
  const relativeFilename = path.relative(outputDir, task.filename);
  assert(relativeFilename && !relativeFilename.startsWith("..") && !path.isAbsolute(relativeFilename), "Completed task wrote outside the isolated directory");
  assert((await stat(task.filename)).size > 0, "Completed file is empty");
  tasks.push({ id: task.id, formatId, status: task.status, progress: task.progress, filename: task.filename });

  assert.equal(await clickButton("Nueva descarga"), true);
  await waitFor("Boolean(document.querySelector('.media-controls select'))", 10000);
  await waitFor("document.querySelector('.warning')?.textContent === 'Este enlace ya aparece en la cola o el historial. Puedes guardar otra copia.'", 10000);
}
assert.equal(new Set(tasks.map(task => path.normalize(task.filename))).size, 3, "Download variants reused a completed filename");

assert.equal(await clickButton("Historial"), true);
await waitFor("document.querySelectorAll('.download-card').length === 3", 30000);
assert.equal(await evaluate("document.querySelector('input[type=search]').closest('label').textContent.trim()"), "Buscar en el historial");
assert.equal(await evaluate("document.querySelector('.history-controls select').closest('label').childNodes[0].textContent.trim()"), "Estado");
await setValue("input[type=search]", "Rammstein");
await waitFor("document.querySelectorAll('.download-card').length === 3", 10000);
await setValue("input[type=search]", "no-matching-smoke-result");
await waitFor("document.querySelectorAll('.download-card').length === 0", 10000);
await setValue("input[type=search]", "");
await setValue(".history-controls select", "failed");
await waitFor("document.querySelectorAll('.download-card').length === 0", 10000);
await setValue(".history-controls select", "completed");
await waitFor("document.querySelectorAll('.download-card').length === 3", 10000);
await screenshot("history-es.png");

console.log(JSON.stringify({
  navigation,
  englishNavigation,
  draftPreserved: true,
  structuredBridgeError: true,
  presets,
  historySearchAndFilter: true,
  inspected: true,
  tasks
}, null, 2));
socket.close();
