/** @jest-environment node */

const { EventEmitter } = require("events");
jest.mock("electron", () => ({
  app: {
    whenReady: jest.fn(() => ({ then: jest.fn() })),
    on: jest.fn(), getPath: jest.fn(() => "D:/temporary/user-data"),
    quit: jest.fn(), isPackaged: false
  },
  protocol: { registerSchemesAsPrivileged: jest.fn(), handle: jest.fn() },
  BrowserWindow: jest.fn(() => ({
    webContents: { mainFrame: {}, setWindowOpenHandler: jest.fn(), on: jest.fn() },
    once: jest.fn(), loadFile: jest.fn()
  })),
  Menu: { setApplicationMenu: jest.fn() },
  ipcMain: { handle: jest.fn() },
  dialog: { showErrorBox: jest.fn() }
}), { virtual: true });
jest.mock("child_process", () => ({ spawn: jest.fn() }));
jest.mock("../../backend-client", () => ({ requestBackend: jest.fn(), waitForBackend: jest.fn().mockResolvedValue() }));
jest.mock("../../runtime-paths", () => ({ resolveFfmpegDirectory: () => "ffmpeg", resolveNodeExecutable: () => "node" }));
jest.mock("../../runtime-contract", () => ({ resolveBackendCommand: () => ({ command: "python", args: [] }), resolveRendererEntry: () => "index.html" }));
jest.mock("../../app-updater", () => ({ configureAppUpdater: jest.fn() }));

let electron;
let spawn;
let requestBackend;
const originalFetch = global.fetch;
let child;
let handlers;

beforeEach(() => {
  jest.clearAllMocks();
  jest.resetModules();
  electron = require("electron");
  ({ spawn } = require("child_process"));
  ({ requestBackend } = require("../../backend-client"));
  handlers = {};
  electron.app.on.mockImplementation((event, callback) => { handlers[event] = callback; });
  child = new EventEmitter();
  Object.assign(child, { pid: 54321, exitCode: null, signalCode: null, kill: jest.fn() });
  spawn.mockReturnValue(child);
  require("../../electron");
});

afterEach(() => { global.fetch = originalFetch; });

async function start() {
  await electron.app.whenReady.mock.results[0].value.then.mock.calls[0][0]();
}

test("registers streaming privileges before ready and a handler after backend readiness", async () => {
  expect(electron.protocol.registerSchemesAsPrivileged).toHaveBeenCalledWith([
    { scheme: "dr-stream", privileges: { standard: true, secure: true, stream: true } }
  ]);
  expect(electron.protocol.handle).not.toHaveBeenCalled();
  await start();
  expect(electron.protocol.handle).toHaveBeenCalledWith("dr-stream", expect.any(Function));
  expect(electron.dialog.showErrorBox).not.toHaveBeenCalled();
});

test("keeps every new operation behind the existing trusted sender boundary", async () => {
  await start();
  const api = electron.ipcMain.handle.mock.calls.find(([channel]) => channel === "dr-download:api")[1];
  await expect(api({ sender: {}, senderFrame: {} }, "startPlayback", {})).rejects.toThrow("Untrusted IPC sender");
  expect(requestBackend).not.toHaveBeenCalled();
});

test("prevents quit until graceful backend cleanup and child exit finish", async () => {
  await start();
  let finishCleanup;
  global.fetch = jest.fn(() => new Promise((resolve) => { finishCleanup = resolve; }));
  const event = { preventDefault: jest.fn() };
  handlers["before-quit"](event);
  expect(event.preventDefault).toHaveBeenCalled();
  expect(electron.app.quit).not.toHaveBeenCalled();
  expect(child.kill).not.toHaveBeenCalled();
  finishCleanup({ ok: true });
  await new Promise(setImmediate);
  expect(electron.app.quit).not.toHaveBeenCalled();
  child.exitCode = 0;
  child.emit("exit", 0);
  await new Promise(setImmediate);
  expect(child.kill).not.toHaveBeenCalled();
  expect(electron.app.quit).toHaveBeenCalledTimes(1);
  expect(global.fetch).toHaveBeenCalledWith(expect.stringMatching(/^http:\/\/127\.0\.0\.1:\d+\/shutdown\/$/), expect.objectContaining({
    method: "POST", signal: expect.any(AbortSignal), headers: { "X-Dr-Download-Token": expect.any(String) }
  }));
  handlers["before-quit"]({ preventDefault: () => { throw new Error("quit still blocked"); } });
});

test("terminates the owned backend tree if graceful shutdown never exits", async () => {
  await start();
  jest.useFakeTimers();
  global.fetch = jest.fn().mockResolvedValue({ ok: true });
  const killer = new EventEmitter();
  spawn.mockImplementation(() => {
    queueMicrotask(() => killer.emit("exit", 0));
    return killer;
  });
  try {
    handlers["before-quit"]({ preventDefault: jest.fn() });
    await jest.runAllTimersAsync();
    if (process.platform === "win32") {
      expect(spawn.mock.calls.at(-1).slice(0, 2)).toEqual(["taskkill", ["/PID", "54321", "/T", "/F"]]);
      expect(spawn.mock.calls.at(-1)[2].windowsHide).toBe(true);
    } else {
      expect(child.kill).toHaveBeenCalledTimes(1);
    }
    expect(electron.app.quit).toHaveBeenCalledTimes(1);
  } finally {
    jest.useRealTimers();
  }
});
