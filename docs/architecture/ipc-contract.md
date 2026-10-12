# Contrato IPC

El renderer solo usa métodos enumerados por `window.drDownload`. No se expone `ipcRenderer`, filesystem ni HTTP.

Operaciones de descarga/configuración: `inspectMedia`, `createDownload`, `listDownloads`, `getDownload`, `cancelDownload`, `retryDownload`, `deleteDownload`, `getConfig`, `updateConfig`, `validateDirectory`, `selectFolder`, `openDownload`, `notify`. La exportación de diagnósticos conserva su operación enumerada existente.

El proceso principal valida sender confiable, identificadores `[A-Za-z0-9_-]{1,128}`, tamaños de entrada y acciones `file|folder`. Nunca acepta una ruta arbitraria desde React.

`createDownload` acepta `estimated_bytes` opcional/null o entero no negativo seguro `<= Number.MAX_SAFE_INTEGER`; rechaza booleanos, fracciones, texto y valores fuera de rango antes de HTTP. El backend repite la validación. `validateDirectory` sigue recibiendo solo `path: string` y devuelve espacio libre para la UI. El campo de estimación no concede permisos ni garantiza espacio final.

Una respuesta de lectura confirmada informa disponibilidad; la existencia de `window.drDownload` no es prueba de backend activo. Las promesas de inspección, encolado y guardado conservan errores y pendientes separados. El renderer mantiene el borrador en memoria; buscar/filtrar y advertir repetición no añade método IPC. No ampliar filesystem ni HTTP genérico para estas funciones.

## Reproducción y listas (implementado; aceptación pendiente, ADR-004)

Operaciones enumeradas: `startPlayback(body)`, `getPlayback(sessionId)`, `stopPlayback(sessionId)`, `listPlaylists()`, `createPlaylist({name})`, `renamePlaylist(id,{name})`, `deletePlaylist(id)`, `addPlaylistItem(id,body)`, `removePlaylistItem(id,itemId)`, `importPlaylist(body)` y `cancelPlaylistImport(requestId)`. Validan UUIDs, nombre 1–100, URL HTTPS de YouTube/Vimeo 8–2048, `cookie_source: none|edge|firefox` y `max_height` entero 144–2160 antes de HTTP; rechazan campos no declarados. Ninguna devuelve URLs de stream, cabeceras ni token. Los cuerpos y respuestas son los del [contrato API](api-contract.md).

`importPlaylist` exige `request_id` UUID generado por `crypto.randomUUID()` en renderer antes de iniciar; `cancelPlaylistImport` usa ese mismo identificador incluso si la resolución sigue pendiente. HTTP 204 se transporta como `null`. Si el commit ya terminó, cancelar rechaza con 409 `playlist_import_completed`: React actualiza las listas y anuncia finalización, sin afirmar cancelación. `getPlayback` expone `actual_start`, estado y causa seguros para confirmar la posición del medio y traducir errores.

El medio no viaja por IPC: main registra antes de `ready` el esquema privilegiado `dr-stream:` (`standard`, `secure`, `stream`) y `protocol.handle` solo acepta `dr-stream://play/<uuid>?start=<decimal finito no negativo>&revision=<entero>`; rechaza exponentes, credenciales, puertos, métodos distintos de GET y parámetros adicionales sin contactar al backend. La revisión está acotada a 0–2147483647 y omitirla equivale a cero; la UI siempre envía una revisión creciente por búsqueda. Main reenvía la petición a `GET /playback/{uuid}/stream` añadiendo el token y conservando cancelación/errores, sin seguir redirecciones ni cachear. La CSP del renderer añade únicamente `media-src 'self' dr-stream:`; `connect-src 'none'`, `frame-src 'none'`, ventanas nuevas y navegación siguen bloqueadas. `stream-protocol.js` forma parte de `build.files`.

Main transporta fallos en una envoltura estructurada y preload rechaza con un objeto simple transferible `{ message, detail }`. Tanto IPC como `contextBridge` pueden eliminar propiedades añadidas a `Error`: consumidores leen `reason.detail` y `reason.message`, sin asumir `instanceof Error` ni campos personalizados de una excepción. Un código conocido se traduce; uno desconocido conserva detalle seguro para diagnóstico y muestra causa/recuperación genéricas localizadas, sin excepción cruda.
