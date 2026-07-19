const { contextBridge, ipcRenderer } = require("electron");

const call = (operation, ...args) => ipcRenderer.invoke("dr-download:api", operation, ...args);

contextBridge.exposeInMainWorld("drDownload", Object.freeze({
  inspectMedia: (request) => call("inspectMedia", request),
  createDownload: (request) => call("createDownload", request),
  listDownloads: () => call("listDownloads"),
  getDownload: (id) => call("getDownload", id),
  cancelDownload: (id) => call("cancelDownload", id),
  retryDownload: (id) => call("retryDownload", id),
  deleteDownload: (id) => call("deleteDownload", id),
  getConfig: () => call("getConfig"),
  updateConfig: (config) => call("updateConfig", config),
  validateDirectory: (request) => call("validateDirectory", request),
  selectFolder: () => ipcRenderer.invoke("dr-download:select-folder"),
  openDownload: (id, action) => ipcRenderer.invoke("dr-download:open-download", id, action),
  exportDiagnostics: () => ipcRenderer.invoke("dr-download:export-diagnostics"),
  notify: (title, body) => ipcRenderer.invoke("dr-download:notify", { title, body })
}));
