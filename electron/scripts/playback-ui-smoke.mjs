import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

function durationOption(value = "15") {
  assert(/^[0-9]+$/.test(value) && Number(value) >= 1 && Number(value) <= 3600,
    "Duration must be an integer from 1 to 3600 seconds");
  return Number(value);
}
function localRendererRequest(url) {
  return /^(?:file:|data:|dr-stream:\/\/play\/)/.test(url);
}
function decodedSeekSeconds(stats, actual, requested, begun) {
  const frame = stats.frames.find((value) => value.mediaTime + 0.001 >= requested - actual);
  assert(frame && Number.isFinite(stats.seekReadyAt), "Requested decoded frame was not shown after preroll");
  return (Math.max(frame.at, stats.seekReadyAt) - begun) / 1000;
}
if (process.argv.includes("--self-test")) {
  assert.equal(durationOption("600"), 600);
  for (const value of ["NaN", "0", "-1", "3601", "1.5", "true"]) assert.throws(() => durationOption(value));
  for (const url of ["file:///app/index.html", "data:image/png;base64,x", "dr-stream://play/session?start=0"]) assert(localRendererRequest(url));
  for (const url of ["https://youtube.com/player.js", "https://googleads.g.doubleclick.net/ad", "http://127.0.0.1:8000/playback"]) assert(!localRendererRequest(url));
  assert.equal(decodedSeekSeconds({ frames: [{ at: 2000, mediaTime: 1 }, { at: 3000, mediaTime: 2 }], seekReadyAt: 3050 }, 13.23, 15.23, 1000), 2.05);
  assert.throws(() => decodedSeekSeconds({ frames: [], seekReadyAt: 1000 }, 0, 15.23, 0));
  assert.throws(() => decodedSeekSeconds({ frames: [{ at: 1000, mediaTime: 20 }] }, 0, 15.23, 0));
  console.log("Playback smoke self-check passed");
  process.exit(0);
}

const [portText, outputDirectory, artifactDirectory, ...options] = process.argv.slice(2);
const seconds = durationOption(options.find((value) => value.startsWith("--duration="))?.slice(11));
const sources = options.filter((value) => !value.startsWith("--"));
const verifyPersistence = options.includes("--verify-persistence");
assert(portText && outputDirectory && artifactDirectory && (verifyPersistence || sources.length === 2),
  "Usage: playback-ui-smoke.mjs <debug-port> <isolated-output> <artifacts> <youtube-url> <vimeo-url> [--duration=600]");
const artifacts = path.resolve(artifactDirectory);
await mkdir(artifacts, { recursive: true });
const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const evidence = { schema: 1, kind: "real-electron-playback-ui", status: "failed", publishable: false,
  started_at_utc: new Date().toISOString(), sustained_seconds_per_provider: { youtube: seconds, vimeo: Math.min(seconds, 15) },
  acceptance_scope: "Current executable and profile only; installed clean Windows and signed release acceptance remain separate",
  videos: [], requests: [], responses: [], request_failures: [], checks: [], threshold_failures: [] };
let socket;
let sequence = 0;
const pending = new Map();

async function command(method, params = {}, timeout = 30000) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Debugger timeout: ${method}`)); }, timeout);
    pending.set(id, {
      resolve: (result) => { clearTimeout(timer); resolve(result); },
      reject: (error) => { clearTimeout(timer); reject(error); }
    });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression, timeout) {
  const response = await command("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }, timeout);
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
  return response.result.value;
}
async function waitFor(expression, timeout = 120000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const result = await evaluate(`Boolean(${expression})`);
    if (result) return result;
    const mediaError = await evaluate("document.querySelector('video')?.error?.code || null");
    if (mediaError) throw new Error(`Chromium media error ${mediaError} while waiting for ${expression}`);
    assert.notEqual(await evaluate("document.querySelector('.playback-workspace .status-chip')?.textContent"),
      "Playback error", `Application reported playback failure while waiting for ${expression}`);
    await delay(200);
  }
  throw new Error(`Timed out waiting for ${expression}`);
}
async function click(label) {
  assert.equal(await evaluate(`(() => {
    const button = [...document.querySelectorAll('button')].find(item => item.getClientRects().length && item.textContent.trim() === ${JSON.stringify(label)});
    if (!button || button.disabled) return false;
    button.click(); return true;
  })()`), true, `Unavailable button: ${label}`);
}
async function setValue(selector, value) {
  assert.equal(await evaluate(`(() => {
    const input = document.querySelector(${JSON.stringify(selector)});
    if (!input || input.disabled) return false;
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, ${JSON.stringify(String(value))});
    input.dispatchEvent(new Event('input', { bubbles: true })); return true;
  })()`), true, `Unavailable input: ${selector}`);
}
async function screenshot(name) {
  const result = await command("Page.captureScreenshot", { format: "png" });
  await writeFile(path.join(artifacts, name), Buffer.from(result.data, "base64"));
}
const snapshot = `(() => { const video = document.querySelector('video'); if (!video) return null;
  return { src: video.getAttribute('src'), time: video.currentTime, paused: video.paused, muted: video.muted,
    title: document.querySelector('.player-stage h2')?.textContent,
    width: video.videoWidth, height: video.videoHeight, readyState: video.readyState, error: video.error?.code || null,
    position: Number(document.querySelector('.player-timeline input')?.value), quality: { totalVideoFrames: video.getVideoPlaybackQuality().totalVideoFrames, droppedVideoFrames: video.getVideoPlaybackQuality().droppedVideoFrames },
    stats: window.__playbackSmoke.videos[video.getAttribute('src')] }; })()`;

try {
  let page;
  const deadline = Date.now() + 150000;
  while (Date.now() < deadline) {
    try {
      const targets = await fetch(`http://127.0.0.1:${Number(portText)}/json/list`, { signal: AbortSignal.timeout(2000) }).then((response) => response.json());
      page = targets.find((target) => target.type === "page" && target.webSocketDebuggerUrl);
      if (page) break;
    } catch { /* The owned app may still be starting its backend. */ }
    await delay(500);
  }
  assert(page, "Electron did not expose its renderer");
  socket = new WebSocket(page.webSocketDebuggerUrl);
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const result = pending.get(message.id); pending.delete(message.id);
      if (message.error) result.reject(new Error(message.error.message)); else result.resolve(message.result);
    } else if (message.method === "Network.requestWillBeSent") {
      evidence.requests.push({ url: message.params.request.url, type: message.params.type });
    } else if (message.method === "Network.responseReceived") {
      const response = message.params.response;
      const headers = Object.fromEntries(Object.entries(response.headers).filter(([name]) => ["content-type", "cache-control", "x-stream-start"].includes(name.toLowerCase())));
      evidence.responses.push({ url: response.url, status: response.status, mime: response.mimeType, headers });
    } else if (message.method === "Network.loadingFailed") {
      evidence.request_failures.push({ type: message.params.type, cause: message.params.errorText, cancelled: message.params.canceled || false });
    }
  });
  socket.addEventListener("close", () => { for (const item of pending.values()) item.reject(new Error("Electron debugger disconnected")); pending.clear(); });
  await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
  await command("Runtime.enable"); await command("Network.enable");
  await waitFor("window.drDownload && document.querySelector('.engine-engineReady')", 30000);
  const config = await evaluate("window.drDownload.getConfig()");
  assert.equal(path.resolve(config.output_dir), path.resolve(outputDirectory), "Backend profile is not isolated; refusing mutations");
  assert.equal(config.cookie_source, "none"); assert.equal(config.cookie_consent, false);
  assert.equal(config.sponsorblock_consent, false); assert.equal(config.language, "en");
  const navigation = await evaluate("[...document.querySelectorAll('nav button span')].map(item => item.textContent.trim())");
  assert.deepEqual(navigation, ["New download", "Queue", "History", "Settings", "About", "Player", "Playlists"]);
  const remoteElements = await evaluate("[...document.querySelectorAll('iframe,script[src]')].map(item => item.src).filter(url => !url.startsWith('file:'))");
  assert.deepEqual(remoteElements, [], "Renderer embeds provider code");

  if (verifyPersistence) {
    const previous = JSON.parse(await (await import("node:fs/promises")).readFile(path.join(artifacts, "evidence.json"), "utf8"));
    const lists = await evaluate("window.drDownload.listPlaylists()");
    const persisted = lists.find((item) => item.id === previous.playlist.id);
    assert.deepEqual(persisted, previous.playlist, "SQLite playlist changed across app restart");
    evidence.playlist = persisted;
    evidence.checks.push("playlist survives real application restart");
  } else {
    await evaluate(`(() => {
      window.__playbackSmoke = { videos: {} };
      const watch = video => {
        if (video.dataset.smokeObserved) return;
        video.dataset.smokeObserved = 'true';
        const src = video.getAttribute('src');
        const stats = { createdAt: performance.now(), firstFrameAt: null, lastFrameAt: null, lastFrameMediaTime: null, presentedFrames: 0, events: [], frames: [] };
        window.__playbackSmoke.videos[src] = stats;
        for (const name of ['waiting','stalled','playing','pause','ended','error']) video.addEventListener(name, () => stats.events.push({ name, at: performance.now(), mediaTime: video.currentTime, error: video.error?.code || null }));
        const frame = (now, metadata) => {
          stats.firstFrameAt ??= now; stats.lastFrameAt = now; stats.lastFrameMediaTime = metadata.mediaTime; stats.presentedFrames = metadata.presentedFrames;
          stats.frames.push({ at: now, mediaTime: metadata.mediaTime });
          if (stats.frames.length > 600) stats.frames.shift();
          if (video.isConnected) video.requestVideoFrameCallback(frame);
        };
        video.requestVideoFrameCallback(frame);
        if (video.style.visibility === 'hidden') new MutationObserver(() => {
          if (video.style.visibility === 'visible') stats.seekReadyAt ??= performance.now();
        }).observe(video, { attributes: true, attributeFilter: ['style'] });
      };
      new MutationObserver(() => document.querySelectorAll('video').forEach(watch)).observe(document.body, { subtree: true, childList: true });
      document.querySelectorAll('video').forEach(watch);
    })()`);
    await click("Playlists");
    await waitFor("document.querySelector('#new-list-name') && !document.querySelector('#new-list-name').disabled");
    const name = "Playback smoke " + Date.now();
    await setValue("#new-list-name", name); await click("Create list");
    await waitFor(`document.querySelector('.playlist-detail h2')?.textContent === ${JSON.stringify(name)}`);
    let playlist = await evaluate(`window.drDownload.listPlaylists().then(items => items.find(item => item.name === ${JSON.stringify(name)}))`);
    for (const [index, url] of [...sources, sources[0]].entries()) {
      await waitFor("!document.querySelector('#list-item-url').disabled");
      await setValue("#list-item-url", url); await click("Add to list");
      await waitFor(`document.querySelectorAll('.playlist-items li').length === ${index + 1}`);
    }
    assert.equal(await evaluate(`window.drDownload.listPlaylists().then(items => items.find(item => item.id === ${JSON.stringify(playlist.id)}).items.length)`), 3);
    await waitFor("!document.querySelector('#rename-list').disabled");
    await setValue("#rename-list", name + " renamed"); await click("Save name");
    await waitFor(`document.querySelector('.playlist-detail h2')?.textContent === ${JSON.stringify(name + " renamed")}`);
    await waitFor("!document.querySelector('.playlist-items li:last-child button:last-child').disabled");
    await evaluate("document.querySelector('.playlist-items li:last-child button:last-child').click()");
    await waitFor("document.querySelectorAll('.playlist-items li').length === 2");
    playlist = await evaluate(`window.drDownload.listPlaylists().then(items => items.find(item => item.id === ${JSON.stringify(playlist.id)}))`);
    assert.deepEqual(playlist.items.map((item) => item.url), sources);
    evidence.playlist = playlist; evidence.checks.push("real UI create, add, duplicate, rename, remove and SQLite read");

    for (const [index, source] of sources.entries()) {
      const observationSeconds = index === 0 ? seconds : Math.min(seconds, 15);
      await click("Player"); await waitFor("Boolean(document.querySelector('#playback-url'))");
      await setValue("#playback-url", source);
      const begun = await evaluate("(() => { const at = performance.now(); document.querySelector('#playback-url').form.requestSubmit(); return at; })()");
      await waitFor("document.querySelector('video') && window.__playbackSmoke.videos[document.querySelector('video').getAttribute('src')]?.firstFrameAt != null");
      await waitFor("!document.querySelector('video').paused && document.querySelector('video').currentTime > 0");
      const initial = await evaluate(snapshot);
      const item = { source, initial, first_frame_seconds: (initial.stats.firstFrameAt - begun) / 1000 };
      evidence.videos.push(item);
      assert(!initial.error && initial.width > 0 && initial.stats.presentedFrames > 0, "Chromium did not decode video");
      if (item.first_frame_seconds > 8) evidence.threshold_failures.push(`First decoded frame exceeded 8 s: ${item.first_frame_seconds}`);
      await screenshot(`provider-${index + 1}-playing.png`);
      await click("Mute"); assert.equal((await evaluate(snapshot)).muted, true);
      await click("Unmute"); assert.equal((await evaluate(snapshot)).muted, false);
      await click("Pause"); await waitFor("document.querySelector('video').paused");
      const pausedAt = (await evaluate(snapshot)).time; await delay(700);
      assert(Math.abs((await evaluate(snapshot)).time - pausedAt) < 0.1, "Pause continued playing");
      await setValue(".player-timeline input", 20.5);
      await waitFor("document.querySelector('video')?.getAttribute('src').includes('?start=20.5&revision=') && document.querySelector('video').readyState >= 3 && !document.querySelector('.player-controls button').disabled");
      item.paused_seek = await evaluate(snapshot);
      assert.equal(item.paused_seek.paused, true); assert(Math.abs(item.paused_seek.position - 20.5) < 0.2);
      await click("Resume"); await waitFor("!document.querySelector('video').paused && document.querySelector('video').currentTime > 0");
      const seekBegun = await evaluate("performance.now()");
      await setValue(".player-timeline input", 15.23);
      await waitFor("document.querySelector('video')?.getAttribute('src').includes('?start=15.23&revision=') && !document.querySelector('video').paused && Number(document.querySelector('.player-timeline input')?.value) >= 15.23 && window.__playbackSmoke.videos[document.querySelector('video').getAttribute('src')]?.lastFrameAt != null");
      const seekMetadata = await evaluate("window.drDownload.getPlayback(document.querySelector('video').getAttribute('src').split('/').at(-1).split('?')[0])");
      await waitFor(`window.__playbackSmoke.videos[document.querySelector('video').getAttribute('src')]?.lastFrameMediaTime >= ${Math.max(0, 15.23 - seekMetadata.actual_start - 0.1)}`);
      const resumed = await evaluate(snapshot);
      item.seek = { requested: 15.23, resumed, seconds: decodedSeekSeconds(resumed.stats, seekMetadata.actual_start, 15.23, seekBegun) };
      if (item.seek.seconds > 5) evidence.threshold_failures.push(`Decoded seek exceeded 5 s: ${item.seek.seconds}`);
      const activeSrc = resumed.src;
      await click("Settings"); await click("Player");
      assert.equal((await evaluate(snapshot)).src, activeSrc, "Navigation replaced playback");
      const sustainStart = await evaluate("performance.now()");
      const sustainedTime = (await evaluate(snapshot)).time;
      for (let elapsed = 0; elapsed < observationSeconds; elapsed += 1) {
        await delay(1000);
        const live = await evaluate(snapshot);
        assert(live && live.src === activeSrc && !live.error && !live.paused, "Playback stopped during sustained observation");
      }
      const sustained = await evaluate(snapshot);
      item.sustained = { seconds: observationSeconds, start_media_time: sustainedTime, end: sustained,
        interruptions: sustained.stats.events.filter((event) => event.at >= sustainStart && ["waiting", "stalled", "error"].includes(event.name)) };
      assert(sustained.time - sustainedTime >= observationSeconds - 2, "Media time did not advance throughout sustained observation");
      assert.equal(item.sustained.interruptions.length, 0, "Playback buffered or failed during sustained observation");
      await click("Close player"); await waitFor("!document.querySelector('video')");
    }
    evidence.checks.push("decoded video, pause, mute, decimal seek, navigation preservation, sustained playback");
    await click("Playlists"); await waitFor("document.querySelector('#selected-list') && !document.querySelector('#selected-list').disabled");
    await evaluate(`(() => { const selected = document.querySelector('#selected-list'); Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(selected, ${JSON.stringify(playlist.id)}); selected.dispatchEvent(new Event('change',{bubbles:true})); })()`);
    await click("Play list"); await waitFor("document.querySelector('video')?.readyState >= 3");
    const firstId = (await evaluate(snapshot)).src.split("/").at(-1).split("?")[0];
    await click("Next"); await waitFor(`document.querySelector('video')?.readyState >= 3 && !document.querySelector('video').getAttribute('src').includes(${JSON.stringify(firstId)})`);
    const nextMetadata = await evaluate(`window.drDownload.getPlayback(document.querySelector('video').getAttribute('src').split('/').at(-1).split('?')[0])`);
    assert.equal(nextMetadata.title, evidence.videos[1].initial.title);
    await click("Previous"); await waitFor(`document.querySelector('video')?.readyState >= 3 && document.querySelector('.player-stage h2')?.textContent === ${JSON.stringify(evidence.videos[0].initial.title)}`);
    const endOfFirst = await evaluate("Number(document.querySelector('.player-timeline input').max) - 0.5");
    await setValue(".player-timeline input", Math.max(0, Math.round(endOfFirst * 100) / 100));
    const previousTitle = await evaluate("document.querySelector('.player-stage h2').textContent");
    await waitFor(`document.querySelector('video')?.readyState >= 3 && document.querySelector('.player-stage h2')?.textContent !== ${JSON.stringify(previousTitle)}`);
    const endOfLast = await evaluate("Number(document.querySelector('.player-timeline input').max) - 0.5");
    await setValue(".player-timeline input", Math.max(0, Math.round(endOfLast * 100) / 100));
    await waitFor("!document.querySelector('video') && document.querySelector('.playback-workspace .status-chip')?.textContent === 'Ended'");
    evidence.checks.push("real playlist Next, Previous, natural advancement and end-of-list stop");
    assert(evidence.requests.some((request) => request.type === "Media" && request.url.startsWith("dr-stream:")), "Chromium made no private media request");
  }
  assert(evidence.requests.every((request) => localRendererRequest(request.url)), "Renderer contacted a remote host");
  evidence.checks.push("renderer requests remain app/private-stream only; provider player/scripts are absent");
  evidence.functional_status = "passed";
  assert.equal(evidence.threshold_failures.length, 0, evidence.threshold_failures.join("; "));
  evidence.status = "passed";
} catch (error) {
  evidence.failure = error.message;
  if (socket?.readyState === WebSocket.OPEN) {
    try { evidence.failure_snapshot = await evaluate(snapshot); } catch { /* A startup failure may precede instrumentation. */ }
    try { await writeFile(path.join(artifacts, "failure-ui.txt"), await evaluate("document.body.innerText")); await screenshot("failure.png"); } catch { /* Preserve the original failure if the app has exited. */ }
  }
} finally {
  evidence.finished_at_utc = new Date().toISOString();
  await writeFile(path.join(artifacts, verifyPersistence ? "persistence-evidence.json" : "evidence.json"), JSON.stringify(evidence, null, 2));
  if (socket?.readyState === WebSocket.OPEN) {
    try { await command("Browser.close", {}, 1000); } catch { /* Closing the browser may close CDP before its reply. */ }
    socket.close();
  }
  console.log(JSON.stringify({ status: evidence.status, failure: evidence.failure, artifacts }));
}
process.exitCode = evidence.status === "passed" ? 0 : 1;
