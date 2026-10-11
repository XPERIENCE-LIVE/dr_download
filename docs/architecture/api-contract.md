# Contrato API local

Todas las rutas requieren `X-Dr-Download-Token` y escuchan solo en `127.0.0.1`.

## `POST /directories/validate`

Entrada: `{ "path": string }`. Crea/comprueba la carpeta, permisos mediante escritura temporal y mínimo de 128 MiB; devuelve espacio libre para la comprobación adicional de la UI.

Salida:

```json
{"accepted":true,"path":"C:\\Users\\...\\Downloads\\Dr. Download","created":true,"writable":true,"free_bytes":0,"error_code":null,"recovery":""}
```

Errores: `invalid_path`, `access_denied`, `disk_full`. La respuesta nunca incluye tokens, cookies ni URL completa.

El preflight de creación de descarga requiere escritura temporal, permisos y espacio libre `>= max(128 * 1024 * 1024, 2 * estimated_bytes)`; omisión/null usa 128 MiB. `estimated_bytes` es asesoría no confiable y no elimina validaciones del backend. Un cliente puede omitirla y el tamaño final puede variar.

## Descargas

`POST /downloads` recibe `url`, `format_id`, `output_dir`, `cookie_source` y `estimated_bytes` opcional/null o entero estricto entre 0 y 9,007,199,254,740,991 inclusive. No admite booleanos, cadenas, fracciones ni valores fuera de rango. Ejecuta el preflight estimado antes de crear ID y encolar. Los estados son `queued`, `inspecting`, `downloading`, `postprocessing`, `completed`, `failed`, `cancelled`.

`POST /media/inspect` devuelve metadatos y formatos disponibles. Cada tamaño estimado ausente se representa como desconocido, no como cero. Presets simples: `video-compatible`, `video-best`, `audio-mp3`; `audio-original` y streams individuales son avanzados. `video-compatible` exige MP4 H.264/AAC y rechaza el caso no disponible sin fallback incompatible. Todos los identificadores enviados siguen validados por el backend. La inspección no crea tarea y no ofrece porcentaje de transferencia.

Filas preset exponen `preset: true` y `estimated_bytes: integer | null`. Las estimaciones usan `filesize`/`filesize_approx` de las fuentes seleccionadas; vídeo sin audio combinado agrega audio, y cualquier componente desconocido mantiene total desconocido. MP3 contempla la conversión sin prometer bytes finales. El preset compatible puede seleccionar un stream ya muxed si también cumple H.264/AAC: es el mismo resultado, no una degradación de codecs. Identificadores directos admiten solo `[A-Za-z0-9_.:-]`, longitud 1–128; se rechazan expresiones selectoras. `estimated_bytes` inválido produce HTTP 422 antes de encolar.

Errores estructurados se traducen por código en la UI con causa y recuperación; no exponer excepciones internas. `PUT /config` confirma persistencia o falla; consentimiento no confirmado no habilita cookies. Revocar aplica a nuevas operaciones. Consultar [experiencia confiable](../product/experience-reliability.md) y [copy](../design/error-copy.md).

`POST /media/inspect` y `POST /downloads` rechazan HTTP 403 con código `browser_consent_required` si se solicita Edge/Firefox y la configuración persistida no contiene `cookie_consent is True` y la misma `cookie_source`. No se acepta autorización por un valor truthy ni por una fuente distinta; no se añaden campos. Recuperación: autorizar el navegador elegido en Ajustes o usar modo sin cookies.

El backend vuelve a consultar la autorización vigente en cola, reintento, worker y construcción del comando antes de leer cookies. Si el consentimiento fue revocado o la fuente cambió, las tareas pendientes/reintentadas usan y registran `none`; no reutilizan la autorización histórica de la tarea. Un proceso ya iniciado puede terminar. La política de tareas cambia tras guardado confirmado: si revocar no se pudo persistir, la UI bloquea nuevos inspect/create con navegador y muestra reintento, pero no promete cambio de configuración backend ni persistencia tras reinicio.

La búsqueda/filtro de historial y el aviso de enlace exacto repetido son locales sobre `GET /downloads`; no añaden endpoints ni prohibición de repetición. Abrir/reintentar sigue resolviendo por ID y mantiene defensa de archivos.

## Reproducción y listas (planificado, ADR-004)

Sin implementar. Definido por el [contrato de reproducción](../product/playback-and-playlists.md); US-067–US-072 siguen `partial`. Todas las rutas exigen el token y validan en backend aunque IPC ya haya validado.

| Ruta | Entrada | Salida | Errores |
|---|---|---|---|
| `POST /playback` | `url` 8–2048, `cookie_source`, `max_height` entero opcional (144–2160, predeterminado 1080) | `{session_id, title, duration, height, sponsor_segments \| null, sponsor_status}`; nunca URLs ni cabeceras del proveedor | `live_unsupported`, `drm_protected`, `stream_unavailable`, 403 `browser_consent_required` |
| `GET /playback/{session_id}/stream?start=<s>` | UUID; `start` entero `0 ≤ start ≤ duration` | `StreamingResponse` `video/mp4` fragmentado | 404 sesión desconocida, 410 `stream_expired`, 422 `start` inválido |
| `DELETE /playback/{session_id}` | UUID | 204; termina el proceso activo | 404 |
| `GET /playlists`, `POST /playlists` | `name` 1–100 tras recortar | listas con conteo de ítems | 422 nombre inválido |
| `PUT /playlists/{id}`, `DELETE /playlists/{id}` | nombre / sin cuerpo | lista actualizada / 204 | 404 |
| `POST /playlists/{id}/items`, `DELETE /playlists/{id}/items/{item_id}` | `url` y metadatos opcionales | ítem con `duplicate: bool` | 404, 422 |
| `POST /playlists/import` | `url`, `cookie_source` | lista creada y resumen `{imported, unavailable}` | `playlist_too_large` con `found`, 403 `browser_consent_required` |

`POST /playback` e importación revalidan el consentimiento estricto por fuente igual que `POST /media/inspect`. Una sesión vive 4 horas en memoria y nunca se persiste. Cada `GET .../stream` termina el proceso anterior de esa sesión antes de iniciar otro; desconectar termina el árbol de procesos. Las rutas que ejecutan el motor son síncronas en el threadpool para no bloquear streams activos; `POST /media/inspect` se corrige con el mismo criterio.

Las rutas antiguas se mantienen como adaptadores durante una versión.
