# Reproducción y listas — contrato de implementación

Decisión de producto aprobada el 2026-10-11 en [ADR-004](../architecture/adr/ADR-004-streaming-playback-and-playlists.md). Las historias US-067–US-072 están `partial` y sin implementar: describen el comportamiento exigido, no certifican su aceptación. La [matriz de aceptación](acceptance-matrix.md), la [trazabilidad](../qa/traceability-matrix.md) y los casos manuales conservan los gaps.

## Reproducir — US-067

- **Origen:** enlaces individuales de YouTube y Vimeo, analizados con el motor incluido. Las emisiones en directo se rechazan con `live_unsupported`; los formatos con DRM, con `drm_protected`. No se reintenta con otro cliente ni se ofrece otra fuente.
- **Calidad:** el backend elige vídeo H.264, VP9 o AV1 y audio AAC u Opus reproducibles por Chromium, hasta la altura elegida (predeterminado 1080p). Si no existe una pareja reproducible responde `stream_unavailable`; no promete compatibilidad por la extensión.
- **Sesión de reproducción:** el backend guarda en memoria las URLs y cabeceras resueltas con un identificador UUID y un TTL de 4 horas, menor que la caducidad habitual de las URLs del proveedor. Al caducar responde `stream_expired` y la interfaz ofrece **Volver a cargar / Reload**, que resuelve de nuevo. Nada de esto se guarda en disco ni llega al renderer.
- **Entrega:** FFmpeg incluido combina vídeo y audio sin recodificar (`-c copy`, MP4 fragmentado) y escribe en la salida estándar; el backend lo transmite con `StreamingResponse`. Electron lo sirve al renderer en `dr-stream://play/<uuid>?start=<segundos>`.
- **Sin anuncios:** no se cargan el reproductor oficial, sus scripts ni sus peticiones de anuncios. No se promete eliminar contenido promocional grabado dentro del vídeo salvo lo que cubre US-069.
- **Sesión con navegador:** si el consentimiento persistido es estrictamente verdadero para la fuente pedida, la resolución usa las cookies de ese navegador; si no, responde 403 `browser_consent_required`, igual que la inspección. El texto de consentimiento advierte el riesgo para la cuenta.
- **Procesos:** cada combinación tiene un único proceso FFmpeg con dueño. Se termina su árbol al desconectar el cliente, al buscar, al cambiar de vídeo y al cerrar la aplicación. Cerrar no deja `ffmpeg.exe` ni `yt-dlp.exe` de reproducción.
- **Estados visibles:** Resolviendo / Resolving (indeterminado, sin porcentaje), Cargando / Buffering, Reproduciendo / Playing, En pausa / Paused, Terminado / Ended y error con causa y recuperación. No se muestra velocidad ni calidad que no se haya confirmado.

## Buscar dentro del vídeo — US-068

- La barra de tiempo es absoluta: posición visible = desplazamiento del último inicio + `currentTime` del elemento de vídeo. Nunca vuelve a cero tras buscar.
- Buscar cancela el proceso anterior y abre un nuevo stream con `start` entero de 0 a la duración conocida. Valores negativos, fraccionarios o mayores que la duración se rechazan en IPC y API.
- Sin duración conocida no se ofrece barra de búsqueda; se indica **Duración desconocida / Duration unknown**.
- La posición real tras buscar puede caer en el fotograma clave anterior; la interfaz muestra la posición real, no la pedida.

## Saltar patrocinios — US-069

- Desactivado por defecto. Activarlo requiere consentimiento propio, persistido con la misma confirmación que las cookies y revocable en Ajustes. Revocar impide consultas nuevas; no promete borrar consultas ya hechas por el servicio externo.
- Antes de implementar se verifica si `yt-dlp --sponsorblock-mark all --dump-single-json` devuelve `sponsorblock_chapters`; si es así se usa el motor único. Si no, el backend consulta la API pública con `httpx` enviando solo el prefijo de 4 caracteres del SHA-256 del identificador (k-anonimato).
- Categorías saltadas: `sponsor`, `selfpromo` e `interaction`. Al entrar en un segmento se busca al final del segmento (mecanismo de US-068) y se anuncia **Patrocinio omitido / Sponsor skipped** con opción de deshacer.
- Si el servicio no responde en 5 s o falla, la reproducción sigue sin saltos y se muestra **Patrocinios no disponibles / Sponsor data unavailable** (`sponsorblock_unavailable`). Es un estado visible, no un cambio silencioso.

## Listas locales — US-070

- Tablas `playlists` e `playlist_items` en la base SQLite existente, creadas con `CREATE TABLE IF NOT EXISTS`. Un fallo de apertura o escritura falla cerrado, como el historial.
- Nombre de lista: 1–100 caracteres tras quitar espacios exteriores; se permiten nombres repetidos porque cada lista tiene su ID.
- Un ítem guarda URL (8–2048 caracteres), título, duración, miniatura y fecha. El stream se resuelve al reproducir, nunca se guarda.
- Se añade desde **Nueva descarga** tras analizar (**Añadir a lista / Add to list**) o pegando un enlace en la lista. Un enlace ya presente se advierte y puede añadirse de nuevo, como el aviso de US-066.
- Renombrar y borrar requieren confirmación de guardado; borrar una lista pide confirmación explícita y no toca archivos descargados.

## Importar listas — US-071

- Un enlace de lista de YouTube o Vimeo se lee con `--flat-playlist --dump-single-json` y crea una lista local nueva con el título de origen.
- Límite: 500 entradas. Si la lista es mayor no se importa nada y se responde `playlist_too_large` con el número de entradas encontrado.
- Entradas privadas, borradas o no disponibles se importan marcadas como no disponibles y se cuentan en el resumen; no se ocultan.
- La importación es una operación indeterminada con cancelación. No se analiza cada vídeo al importar.

## Reproducir una lista — US-072

- Reproduce en el orden de la lista con **Anterior / Previous**, **Siguiente / Next** y avance automático al terminar.
- Un ítem que falla al resolverse se salta con un aviso visible que nombra el ítem y la causa; no se reintenta en bucle. Si fallan todos, la reproducción se detiene con el error.
- Al llegar al final se detiene; la repetición y el orden aleatorio están diferidos.

## Seguridad y privacidad

- El renderer solo conoce identificadores de sesión, listas e ítems. URLs de stream, cabeceras HTTP, cookies y token quedan en backend y main.
- `dr-stream:` solo acepta `play/<uuid>` y `start` entero; cualquier otra forma se rechaza sin contactar al backend.
- La CSP añade únicamente `media-src 'self' dr-stream:`.
- Los registros no contienen URLs de stream, cabeceras ni cookies.

## Umbrales de aceptación

Medidos en el paquete real, Windows 10/11 x64, conexión de 50 Mb/s o superior, vídeo público de YouTube a 1080p y vídeo público de Vimeo:

| Métrica | Umbral |
|---|---|
| Inicio desde **Reproducir** hasta el primer fotograma | ≤ 8 s |
| Buscar hasta reanudar | ≤ 5 s |
| Cortes de reproducción en 10 min continuos | 0 |
| Procesos de reproducción tras cerrar | 0 |
| Importación de una lista de 500 entradas | ≤ 60 s |

## Verificación requerida

Pruebas unitarias y de API con casos de éxito, consentimiento ausente, DRM, directo, caducidad, límites de `start`, límite de importación y fallo de SponsorBlock; pruebas Jest de IPC, protocolo, CSP y vistas; prueba de limpieza de procesos. Las pruebas aisladas no acreditan aceptación. MAN-US-067–MAN-US-072 deben ejecutarse en el paquete real antes de `accepted`. Los nombres de pruebas solo se incorporan a las fichas cuando existan en el inventario.
