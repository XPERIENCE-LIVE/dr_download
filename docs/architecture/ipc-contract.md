# Contrato IPC

El renderer solo usa métodos enumerados por `window.drDownload`. No se expone `ipcRenderer`, filesystem ni HTTP.

Operaciones de descarga/configuración: `inspectMedia`, `createDownload`, `listDownloads`, `getDownload`, `cancelDownload`, `retryDownload`, `deleteDownload`, `getConfig`, `updateConfig`, `validateDirectory`, `selectFolder`, `openDownload`, `notify`. La exportación de diagnósticos conserva su operación enumerada existente.

El proceso principal valida sender confiable, identificadores `[A-Za-z0-9_-]{1,128}`, tamaños de entrada y acciones `file|folder`. Nunca acepta una ruta arbitraria desde React.

`createDownload` acepta `estimated_bytes` opcional/null o entero no negativo seguro `<= Number.MAX_SAFE_INTEGER`; rechaza booleanos, fracciones, texto y valores fuera de rango antes de HTTP. El backend repite la validación. `validateDirectory` sigue recibiendo solo `path: string` y devuelve espacio libre para la UI. El campo de estimación no concede permisos ni garantiza espacio final.

Una respuesta de lectura confirmada informa disponibilidad; la existencia de `window.drDownload` no es prueba de backend activo. Las promesas de inspección, encolado y guardado conservan errores y pendientes separados. El renderer mantiene el borrador en memoria; buscar/filtrar y advertir repetición no añade método IPC. No ampliar filesystem ni HTTP genérico para estas funciones.

Main transporta fallos en una envoltura estructurada y preload rechaza con un objeto simple transferible `{ message, detail }`. Tanto IPC como `contextBridge` pueden eliminar propiedades añadidas a `Error`: consumidores leen `reason.detail` y `reason.message`, sin asumir `instanceof Error` ni campos personalizados de una excepción. Un código conocido se traduce; uno desconocido conserva detalle seguro para diagnóstico y muestra causa/recuperación genéricas localizadas, sin excepción cruda.
