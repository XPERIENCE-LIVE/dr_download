const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  selectFolder: () => ipcRenderer.invoke('select-folder')
});

window.addEventListener('DOMContentLoaded', () => {
  console.log('Electron preload ready');
});
