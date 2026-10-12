# Validación de reproducción y listas — US-067–US-072

La rama contiene servicios, rutas, almacenamiento SQLite, protocolo Electron y vistas React. Esto acredita existencia de implementación, no aceptación del producto. Las seis historias conservan `partial`, sus entradas del ledger `open` y MAN-US-067–MAN-US-072 `pending`. El resultado global, SHA/fingerprint y limitaciones deben leerse en la evidencia de la ejecución concreta; no reutilizar conteos de una ejecución anterior.

La [revalidación posterior](streaming-followup-validation.md) conserva diagnósticos, correcciones, identidades del paquete y resultados reales, incluidos los fallos de pruebas y latencia.

## Inventario ejecutable

| Alcance | Suite y ejemplos existentes | Límite de lo que demuestra |
|---|---|---|
| Formatos, DRM/directo, TTL y metadatos | `backend/tests/test_playback.py`: `test_selects_supported_video_audio_without_drm`, `test_rejects_live_or_protected_media`, `test_hls_audio_with_unknown_codec_is_verified_before_selection`, `test_hls_drm_key_is_rejected_with_explicit_cause`, `test_session_expiry_is_explicit`, `test_session_metadata_never_exposes_upstream_urls_or_headers` | Datos de proveedor controlados; no acredita cada vídeo/códec real |
| Búsqueda y propiedad de procesos | `test_seek_accepts_finite_decimal_seconds`, `test_seek_rejects_untrusted_values`, `test_new_stream_cleanup_cannot_kill_a_replacement`, `test_late_seek_cannot_replace_the_latest_request`, `test_late_browser_retry_cannot_reserve_an_older_source_or_kill_current_process` | Fronteras controladas; la latencia necesita red y Chromium reales |
| FFmpeg real | `test_bundled_ffmpeg_stream_is_decodable_and_owned_process_stops`, `test_bundled_seek_uses_owned_ffmpeg_timestamps_without_a_second_probe`, `test_bundled_http_stream_recovers_or_fails_visibly_after_transport_disconnect` | Herramientas incluidas, fuente sintética y servidor HTTP real que corta la conexión: exige los 150 fotogramas tras recuperar y fallo visible si no recupera. No acredita el proveedor ni el instalador |
| Consentimiento | `test_playback_api_rejects_unconsented_browser_before_engine`, `test_sponsorblock_queries_hash_prefix_only_when_consented`; React `SponsorBlock permission is enabled only after a successful persisted confirmation` | Consentimiento y llamadas aisladas; el segmento externo real requiere MAN-US-069 |
| SQLite y CRUD | `backend/tests/test_playlists.py`: `test_playlist_crud_persists_and_preserves_downloads`, `test_playlist_items_keep_order_allow_duplicates_and_cascade`, `test_playlist_missing_resources_and_storage_failure_are_visible` | SQLite real con perfil temporal; reinicio real del paquete requiere el smoke gráfico de la ejecución concreta |
| Límites y commit de importación | `test_import_over_500_rolls_back_everything`, `test_import_exactly_500_entries_succeeds_atomically`, `test_cancel_import_just_before_commit_is_atomic`, `test_cancel_already_committed_import_reports_completion_without_removing_it`, `test_revoked_cookie_consent_before_commit_prevents_import` | Entradas de extracción controladas; 500 entradas del proveedor y tiempo total aún requieren evidencia |
| Proceso real de importación | `test_import_engine_protocol_reads_json_and_closes_real_process_pipes`, `test_cancel_import_terminates_real_owned_child_and_closes_pipes`, `test_import_bounds_real_child_output_and_cleans_it_up` | Subproceso real controlado; no simula fiabilidad de YouTube/Vimeo |
| IPC y streaming Electron | `electron/src/__tests__/streaming-contract.test.js`, `stream-protocol.test.js`, `electron-playback-lifecycle.test.js`, `backend-client.test.js`, `preload-errors.test.js` | Dobles del transporte/Electron en Jest; exige ejecución real contextBridge/protocolo |
| Reproductor y listas React | `electron/src/__tests__/playback-playlists.test.jsx`: orden, error/omisión, fin, anterior/siguiente, limpieza tardía, offsets decimales, descarte del fotograma clave, pausa, navegación, límite de solicitudes directas, SponsorBlock/deshacer/no_segments, CRUD, errores, cancelación UUID y éxito antes de actualizar listas | DOM de prueba y APIs aisladas; no decodifica medios ni mide primer fotograma |

Las fichas de historias y `docs/ai/change-ledger.json` citan únicamente nombres/suites existentes. Los nombres no equivalen por sí solos a una ejecución aprobada.

## Comandos reproducibles

Desde la raíz:

```powershell
python -m pytest -q backend/tests/test_playback.py backend/tests/test_playlists.py
node electron/node_modules/jest/bin/jest.js --config electron/jest.config.js --runInBand
npm run quality:pr
```

Para suites focalizadas de React/Electron, ejecutar desde `electron`:

```powershell
node node_modules/jest/bin/jest.js --runInBand src/__tests__/playback-playlists.test.jsx src/__tests__/streaming-contract.test.js src/__tests__/stream-protocol.test.js src/__tests__/electron-playback-lifecycle.test.js
npm run lint
npm run build
```

El gate completo determina la regresión de la fuente actual. Usar el perfil temporal normal de pytest; una ruta `--basetemp` personalizada no sustituye la comprobación de higiene del repositorio.

## Evidencia de desarrollo y proveedores

`artifacts/quality/streaming-implementation` conserva las salidas roja/verde de cada dominio, evidencia JSON y salidas de smoke. `ui-red.txt` registra la ausencia inicial de componentes; `ui-direct-navigation-red.txt` el fallo al navegar desde un enlace reproducido directamente; `ui-import-race-red.txt` el falso estado de cancelación después del éxito; `ui-resolution-red.txt` el envío repetido mientras se resuelve. `ui-green.txt` corresponde a una ejecución posterior de esas regresiones. Estos logs focalizados no son evidencia de aceptación del instalador.

`tools/smoke_test_playback.py` inicia el backend real con datos aislados, yt-dlp/Node/FFmpeg/FFprobe incluidos y fuentes autorizadas. Resuelve y descarga fragmentos desde cero y desde un desplazamiento decimal, comprueba medios y ejercita listas/importación según los argumentos. Conserva errores del proveedor sin declararlos éxito. Ejemplo:

```powershell
python tools/smoke_test_playback.py --url "https://www.youtube.com/watch?v=aqz-KE-bpKQ" --url "https://vimeo.com/1084537" --playlist-url "https://www.youtube.com/playlist?list=PLBB231211A4F62143"
```

Su evidencia declara comando, sistema, commit y árbol modificado. Un árbol modificado necesita fingerprint de los archivos probados; `HEAD` aislado no identifica cambios sin commit. Los fallos originales deben conservarse aunque una corrección posterior consiga otro resultado. No registra aceptación de la GUI instalada ni asegura ausencia universal de publicidad: la arquitectura excluye el reproductor y scripts oficiales, pero no elimina contenido ya incorporado en el medio.

## Ejecución gráfica real

`electron/scripts/run-playback-ui-smoke.ps1` usa CDP sobre Electron real y un perfil temporal; `-Packaged` ejecuta `win-unpacked`. Registra fotogramas decodificados y el instante en que el tramo de búsqueda se vuelve visible, pausa, silencio, navegación, CRUD, anterior/siguiente, avance natural, fin de lista y persistencia tras reiniciar. Los umbrales fallidos se conservan y hacen fallar el resultado final, aunque se continúe para comprobar el resto de funciones. La identidad incluye hashes del ejecutable, app.asar, backend, Node, FFmpeg/FFprobe, motor explícito y archivos fuente; también verifica que no cambien durante la ejecución y que no queden procesos propios.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File electron/scripts/run-playback-ui-smoke.ps1 -Packaged -Duration 600 -VimeoUrl "https://vimeo.com/20465972" -EnginePath "artifacts/quality/streaming-implementation/real-api/data/engine/yt-dlp.exe"
```

El ejemplo requiere un motor real previamente verificado en esa ruta; no acredita su instalación inicial. `-Duration 600` exige 600 s por proveedor y falla si la duración del origen no alcanza después de buscar a 15,23 s. El enlace largo de Vimeo se verificó como Elephants Dream, 644 s y 360p; el enlace predeterminado de Vimeo, 1084537, sigue sirviendo para pruebas cortas a 720p pero no permite 600 s después de buscar. Las ejecuciones históricas que limitaron Vimeo a 15 s conservan ese alcance y no se convierten en pruebas de diez minutos. La banda y estabilidad de red no se calibran automáticamente; `win-unpacked` tampoco acredita instalación NSIS.

## Pendientes de aceptación

Completar MAN-US-067–MAN-US-072 en el mismo paquete identificado por SHA-256, con Windows 10/11 x64, escalas e idiomas exigidos y fuentes autorizadas de ambos proveedores. Medir primer fotograma ≤ 8 s, búsqueda ≤ 5 s, cero cortes durante 10 min, importación real de 500 entradas ≤ 60 s y cero procesos de reproducción al cerrar. Verificar teclado/pantalla completa, offset real después de búsquedas rápidas, consentimiento/revocación/timeout con segmento SponsorBlock real, persistencia tras reinicio, errores de proveedor y ausencia de datos sensibles en renderer/logs.

Una combinación no ejecutada sigue pendiente. Commit/push de la rama no publica instalador, no cierra la matriz ni desbloquea firma o release.
