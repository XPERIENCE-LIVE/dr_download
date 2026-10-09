const { app, BrowserWindow, Menu, Notification, dialog, ipcMain, shell } = require("electron");
const crypto = require("crypto");
const fs = require("fs");
const net = require("net");
const path = require("path");
const { spawn } = require("child_process");
const { requestBackend: sendBackendRequest, waitForBackend } = require("./backend-client");
const { resolveDownloadTarget, sanitizeNotification } = require("./file-actions");
const { configureAppUpdater } = require("./app-updater");
const { resolveFfmpegDirectory, resolveNodeExecutable } = require("./runtime-paths");
const { configureNavigationGuards, isTrustedSender, secureWebPreferences } = require("./electron-security");
const { writeDiagnosticReport } = require("./diagnostics");
const { resolveBackendCommand, resolveRendererEntry } = require("./runtime-contract");

let mainWindow;
let backendProcess;
let backendPort;
let sessionToken;

function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

async function startBackend() {
  backendPort = await findFreePort();
  sessionToken = crypto.randomBytes(32).toString("hex");
  const projectRoot = path.resolve(__dirname, "..");
  const { command, args } = resolveBackendCommand(app.isPackaged, process.resourcesPath, process.env, fs.existsSync);
  backendProcess = spawn(command, args, {
    cwd: app.isPackaged ? process.resourcesPath : projectRoot,
    env: {
      ...process.env,
      DR_DOWNLOAD_PORT: String(backendPort),
      DR_DOWNLOAD_TOKEN: sessionToken,
      DR_DOWNLOAD_DATA_DIR: app.getPath("userData"),
      DR_DOWNLOAD_FFMPEG: resolveFfmpegDirectory(app.isPackaged, process.resourcesPath, __dirname, process.env.DR_DOWNLOAD_FFMPEG),
      DR_DOWNLOAD_NODE: resolveNodeExecutable(app.isPackaged, process.resourcesPath, __dirname)
    },
    windowsHide: true,
    stdio: app.isPackaged ? "ignore" : "inherit"
  });
  backendProcess.once("exit", () => { backendProcess = null; });
  await waitForBackend(`http://127.0.0.1:${backendPort}`, sessionToken, backendProcess);
}

async function requestBackend(operation, args) {
  return sendBackendRequest(`http://127.0.0.1:${backendPort}`, sessionToken, operation, args);
}

function assertTrustedSender(event) {
  if (!isTrustedSender(event, mainWindow)) throw new Error("Untrusted IPC sender");
}

function registerIpc() {
  ipcMain.handle("dr-download:api", async (event, operation, ...args) => {
    assertTrustedSender(event);
    try {
      return await requestBackend(operation, args);
    } catch (error) {
      // Electron serializes thrown errors without their custom detail fields.
      if (error.detail && typeof error.detail === "object" && !Array.isArray(error.detail)) {
        return { drDownloadError: error.detail };
      }
      throw error;
    }
  });
  ipcMain.handle("dr-download:select-folder", async (event) => {
    assertTrustedSender(event);
    const result = await dialog.showOpenDialog(mainWindow, { properties: ["openDirectory", "createDirectory"] });
    return result.canceled ? null : result.filePaths[0];
  });
  ipcMain.handle("dr-download:open-download", async (event, id, action) => {
    assertTrustedSender(event);
    const record = await requestBackend("getDownload", [id]);
    const target = resolveDownloadTarget(record, action);
    if (!fs.existsSync(target)) throw new Error("Recorded download target does not exist");
    const failure = await shell.openPath(target);
    if (failure) throw new Error(failure);
    return true;
  });
  ipcMain.handle("dr-download:notify", async (event, payload) => {
    assertTrustedSender(event);
    if (Notification.isSupported()) new Notification(sanitizeNotification(payload)).show();
  });
  ipcMain.handle("dr-download:export-diagnostics", async (event) => {
    assertTrustedSender(event);
    const result = await dialog.showSaveDialog(mainWindow, {
      defaultPath: `Dr-Download-diagnostics-${Date.now()}.txt`,
      filters: [{ name: "Text", extensions: ["txt"] }]
    });
    if (result.canceled || !result.filePath) return false;
    writeDiagnosticReport(path.join(app.getPath("userData"), "logs"), result.filePath, {
      version: app.getVersion(), platform: process.platform, arch: process.arch
    });
    return true;
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 820,
    minHeight: 620,
    backgroundColor: "#0b0d10",
    title: "Dr. Download",
    titleBarStyle: "hidden",
    titleBarOverlay: { color: "#0b0d10", symbolColor: "#f1eee6", height: 36 },
    show: false,
    webPreferences: secureWebPreferences(path.join(__dirname, "preload.js"))
  });
  configureNavigationGuards(mainWindow.webContents);
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.loadFile(resolveRendererEntry(__dirname, fs.existsSync));
}

async function stopBackend() {
  if (!backendProcess) return;
  try {
    await fetch(`http://127.0.0.1:${backendPort}/shutdown/`, {
      method: "POST", headers: { "X-Dr-Download-Token": sessionToken }
    });
  } catch (error) {
    console.error("Backend rejected the graceful shutdown request", error.name);
  }
  if (backendProcess) backendProcess.kill();
}

app.whenReady().then(async () => {
  Menu.setApplicationMenu(null);
  registerIpc();
  try {
    await startBackend();
    createWindow();
    configureAppUpdater({
      app,
      dialog,
      listDownloads: () => requestBackend("listDownloads", [])
    });
  } catch (error) {
    dialog.showErrorBox("Dr. Download", error.message);
    app.quit();
  }
});

app.on("before-quit", stopBackend);
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

module.exports = { findFreePort };
