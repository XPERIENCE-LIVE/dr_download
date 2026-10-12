# Arquitectura

La validación de destino vive en `backend/directory_service.py` y se expone por `POST /directories/validate`. Tanto esa ruta como `POST /downloads` crean la carpeta predeterminada, realizan una escritura temporal y verifican el espacio mínimo antes de permitir la cola. React solo recibe el resultado estructurado mediante el contrato IPC enumerado.

La estimación opcional no negativa validada por API/IPC eleva el mínimo de creación de tarea a `max(128 MiB, 2 * estimated_bytes)`; React también compara ese umbral con el espacio libre devuelto por validación de carpeta. No cambia la política de ruta, escritura ni colisiones. El [contrato de experiencia](../product/experience-reliability.md) mantiene borrador y búsqueda/filtro en React, confirmación/errores en las operaciones existentes y presets/validación en backend; no añade servicio, dependencia ni endpoint para historial.

```text
React renderer (sandbox)
        │ operaciones enumeradas
        ▼
Electron preload / main ── select folder, open path, notifications
        │ HTTP 127.0.0.1 + token aleatorio + puerto dinámico
        ▼
FastAPI ── cola ── yt-dlp.exe actualizable obligatorio
   └── SQLite + preferencias locales
```

## Reproducción y listas (implementado; aceptación pendiente, ADR-004)

[ADR-004](adr/ADR-004-streaming-playback-and-playlists.md) aprueba reproducir sin el reproductor oficial y gestionar listas; el [contrato](../product/playback-and-playlists.md) fija límites. La implementación vive en `backend/playback_service.py`, `playback_routes.py`, `playlist_routes.py`, `store.py`, `electron/stream-protocol.js` y las vistas React `Playback`/`Playlists`. Las historias siguen `partial` hasta aceptación del paquete real.

```text
<video src="dr-stream://play/<uuid>?start=s&revision=n">   (renderer, CSP media-src dr-stream:)
        │
Electron main: protocol.handle valida forma, añade token
        │ HTTP 127.0.0.1
        ▼
FastAPI GET /playback/{uuid}/stream
        │ sesión en memoria (URLs + cabeceras, TTL 4 h)
        ▼
ffmpeg.exe incluido: -ss s, vídeo + audio, -c copy, MP4 fragmentado → stdout
        ▲
yt-dlp.exe incluido resolvió los streams en POST /playback (consentimiento estricto)
```

Buscar = terminar el proceso y abrir otro stream en el nuevo `start` decimal finito. El propio FFmpeg confirma el tiempo del primer paquete de vídeo, sin una segunda consulta de búsqueda; `GET /playback/{uuid}` devuelve `actual_start`. La UI decodifica el tramo inicial a 4×, oculto y silenciado, reduciendo a 1× durante el último medio segundo para evitar sobrepasar el destino, y usa `requestVideoFrameCallback` para mostrar/reanudar desde el punto pedido; conserva la pausa solicitada. Las listas viven en tablas `playlists` y `playlist_items` del mismo SQLite; la importación usa el motor con `--flat-playlist`, UUID de operación y commit atómico. SponsorBlock es opcional, con consentimiento propio, y su fallo se muestra sin detener el vídeo. La inspección y resolución bloqueantes se ejecutan fuera del event loop.

## Seguridad

El renderer no recibe `ipcRenderer`, filesystem ni una función HTTP genérica. `ipc-contract.js` transforma únicamente operaciones conocidas. Electron valida el `webContents` emisor; el backend exige `X-Dr-Download-Token` cuando lo inicia la aplicación. CSP bloquea conexiones del renderer, ventanas nuevas y navegación.

Consentimiento se comprueba en backend por fuente y booleano persistido estrictamente verdadero al inspeccionar/crear y antes de lectura en cola/retry/worker/comando. Main/preload transportan fallos como envoltura/rechazo simple message/detail que sobrevive IPC/contextBridge; React traduce el código sin asumir una instancia Error. [API](api-contract.md) e [IPC](ipc-contract.md) detallan rechazos, revocación y límites.

## API

- `POST /media/inspect`
- `POST /downloads`
- `GET /downloads` y `/downloads/{id}`
- `POST /downloads/{id}/cancel` y `/retry`
- `DELETE /downloads/{id}`
- `GET /config/` y `PUT /config`
- Adaptadores temporales: `/download/`, `/progress/{id}`, `/history/` y `POST /config/`.

Estados: `queued`, `inspecting`, `downloading`, `postprocessing`, `completed`, `failed`, `cancelled`.

## Persistencia y actualización

SQLite guarda el payload de cada tarea; el JSON histórico se importa una sola vez y se respalda como `.bak`. El actualizador del motor comprueba como máximo cada 24 horas, verifica `SHA2-256SUMS`, ejecuta `--version`, conserva `.previous` y reemplaza atómicamente.

El runtime es fail-closed: durante el primer arranque el backend no publica salud ni acepta trabajo hasta tener un yt-dlp.exe descargado, verificado por SHA-256 y aprobado por `--version`. Si falta yt-dlp.exe, Node, backend empaquetado o el HTML compilado canónico, la aplicación muestra un error y detiene la operación. No cambia a otro motor, runtime o layout.

El transporte HTTP(S) admite como máximo dos reconexiones al mismo origen por incidente, con espera acumulada de dos segundos; no activa reconexión al EOF ni ante denegaciones HTTP. Un error recuperado solo permite fin correcto si FFmpeg termina con código cero y ambas pistas alcanzan la duración conocida. Las trazas de tiempo se leen y descartan en memoria; solo se retienen hasta 64 KiB de errores para clasificarlos sin exponer texto crudo.

Cada intención de búsqueda lleva una revisión entera creciente en la URL privada. El backend rechaza con 409 una revisión inferior a la más reciente antes de tocar el proceso actual: un reintento tardío de Chromium no puede sustituir la búsqueda nueva. Los eventos tardíos de elementos anteriores se descartan; un EOF anterior a la duración conocida o sin estado backend `ended` se trata como fallo, sin avanzar la lista.
