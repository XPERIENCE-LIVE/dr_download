const { contextBridge, ipcRenderer } = require("electron");

const call = async (operation, ...args) => {
  const result = await ipcRenderer.invoke("dr-download:api", operation, ...args);
  if (result?.drDownloadError) {
    // contextBridge also drops custom Error fields; reject transferable data.
    return Promise.reject({ message: result.drDownloadError.message || "Backend operation failed", detail: result.drDownloadError });
  }
  return result;
};

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
