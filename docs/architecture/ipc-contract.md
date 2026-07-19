# Contrato IPC

El renderer solo usa métodos enumerados por `window.drDownload`. No se expone `ipcRenderer`, filesystem ni HTTP.

Operaciones: `inspectMedia`, `createDownload`, `listDownloads`, `getDownload`, `cancelDownload`, `retryDownload`, `deleteDownload`, `getConfig`, `updateConfig`, `selectFolder`, `openDownload`, `notify`.

El proceso principal valida sender confiable, identificadores `[A-Za-z0-9_-]{1,128}`, tamaños de entrada y acciones `file|folder`. Nunca acepta una ruta arbitraria desde React.
