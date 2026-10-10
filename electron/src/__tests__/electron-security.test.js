/** @jest-environment node */

const {
  configureNavigationGuards,
  isTrustedSender,
  secureWebPreferences
} = require("../../electron-security");

test("trusts IPC only from the main frame of the application window", () => {
  const mainFrame = {};
  const webContents = { mainFrame };
  const mainWindow = { webContents };

  expect(isTrustedSender({ sender: webContents, senderFrame: mainFrame }, mainWindow)).toBe(true);
  expect(isTrustedSender({ sender: webContents, senderFrame: {} }, mainWindow)).toBe(false);
  expect(isTrustedSender({ sender: {}, senderFrame: mainFrame }, mainWindow)).toBe(false);
  expect(isTrustedSender({ sender: webContents, senderFrame: mainFrame }, null)).toBe(false);
});

test("blocks popups and every renderer navigation", () => {
  const callbacks = {};
  const webContents = {
    setWindowOpenHandler: jest.fn((callback) => { callbacks.open = callback; }),
    on: jest.fn((name, callback) => { callbacks[name] = callback; })
  };
  configureNavigationGuards(webContents);

  const event = { preventDefault: jest.fn() };
  expect(callbacks.open()).toEqual({ action: "deny" });
  callbacks["will-navigate"](event);
  expect(event.preventDefault).toHaveBeenCalled();
});

test("returns hardened renderer preferences", () => {
  expect(secureWebPreferences("C:/app/preload.js")).toEqual({
    preload: "C:/app/preload.js",
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
    webSecurity: true
  });
});
