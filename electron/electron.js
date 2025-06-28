const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  // The compiled React app outputs index.html in dist/public
  // Use an absolute path so packaged builds work reliably
  const indexPath = path.resolve(__dirname, "dist", "public", "index.html");
  if (require("fs").existsSync(indexPath)) {
    win.loadFile(indexPath);
  } else {
    win.loadURL("data:text/html,Please run 'npm run build' first.");
  }
}

ipcMain.handle('select-folder', async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog({
    properties: ['openDirectory']
  });
  return canceled ? null : filePaths[0];
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
