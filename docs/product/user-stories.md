# Historias de usuario

## E1 — Destino confiable

### US-001 — Carpeta inicial válida

- **ID:** US-001
- **Épica:** E1 — Destino confiable.
- **Persona:** usuario que inicia Dr. Download por primera vez.
- **Problema:** una configuración vacía no debe producir un fallo tardío al encolar.
- **Precondiciones:** perfil de Windows disponible y aplicación iniciada sin carpeta guardada.
- **Flujo principal:** cargar configuración → resolver `%USERPROFILE%\\Downloads\\Dr. Download` → crear carpeta → probar escritura y espacio → persistir ruta aceptada.
- **Flujos alternativos:** perfil inaccesible o volumen con menos de 128 MB devuelve error estructurado; no se habilita la cola.
- **Given/When/Then:** Given no existe configuración de salida, When se abre Nueva descarga, Then se crea y valida la carpeta predeterminada. Given la creación falla, When termina el preflight, Then la UI explica causa y recuperación sin encolar.
- **Prueba unitaria:** `test_ensure_output_directory_creates_missing_directory`; `test_load_config_defaults`.
- **Prueba de integración:** `test_validate_directory_endpoint_creates_directory`.
- **Prueba E2E:** `MAN-US-001`: primer arranque instalado en un perfil limpio de Windows.
- **Evidencia requerida:** respuesta `DirectoryCheck`, carpeta real creada y reporte del instalador con sistema/configuración.
- **Riesgos:** perfiles redirigidos por políticas corporativas o protección antiransomware.

### US-002 — Elegir y validar carpeta

- **ID:** US-002
- **Épica:** E1 — Destino confiable.
- **Persona:** usuario que necesita guardar el archivo en otra ubicación.
- **Problema:** Windows puede mostrar una carpeta que no está disponible o no permite escritura.
- **Precondiciones:** diálogo nativo accesible y medio inspeccionado o formulario activo.
- **Flujo principal:** elegir carpeta → normalizar ruta absoluta → crear si corresponde → escribir/eliminar archivo temporal → medir espacio → persistir solo si es aceptada.
- **Flujos alternativos:** cancelación conserva la ruta anterior; unidad ausente, archivo o acceso denegado devuelve código y recuperación.
- **Given/When/Then:** Given una carpeta escribible, When se selecciona, Then queda validada inmediatamente. Given una ruta inválida, When se valida, Then `accepted=false` y Agregar a la cola permanece deshabilitado.
- **Prueba unitaria:** `test_ensure_output_directory_rejects_existing_file`; `test_ensure_output_directory_enforces_free_space`.
- **Prueba de integración:** `test_create_download_returns_structured_directory_error`.
- **Prueba E2E:** `MAN-US-002`: carpeta local, unidad ausente y carpeta protegida en Windows.
- **Evidencia requerida:** respuestas reales para cada ruta y captura accesible del botón deshabilitado.
- **Riesgos:** permisos que cambian entre preflight y escritura final.

### US-003 — Recuperar carpeta inválida sin perder contexto

- **ID:** US-003
- **Épica:** E1 — Destino confiable.
- **Persona:** usuario cuya carpeta configurada dejó de estar disponible.
- **Problema:** corregir el destino no debe obligar a repetir la inspección.
- **Precondiciones:** medio inspeccionado y `DirectoryCheck.accepted=false`.
- **Flujo principal:** mostrar causa → pulsar Usar carpeta Descargas → validar destino predeterminado → conservar metadatos y formato → habilitar cola.
- **Flujos alternativos:** si la carpeta predeterminada también falla se mantiene el error y se ofrece Elegir otra carpeta.
- **Given/When/Then:** Given una inspección visible y destino inválido, When se recupera con Descargas, Then el medio inspeccionado permanece y solo cambia la ruta. Given la recuperación falla, When finaliza, Then no se envía `POST /downloads`.
- **Prueba unitaria:** `validates the destination before queueing`.
- **Prueba de integración:** contrato IPC validateDirectory seguido de updateConfig únicamente con resultado aceptado.
- **Prueba E2E:** `MAN-US-003`: desconectar el destino, recuperar y encolar sin reinspeccionar.
- **Evidencia requerida:** secuencia IPC real y captura antes/después con el mismo título inspeccionado.
- **Riesgos:** carrera entre cambio de unidad y creación de descarga.

### US-004 — Defensa de destino en backend

- **ID:** US-004
- **Épica:** E1 — Destino confiable.
- **Persona:** operador responsable de la frontera de seguridad local.
- **Problema:** un renderer manipulado no puede eludir el preflight de filesystem.
- **Precondiciones:** token de sesión válido y payload enviado directamente a la API local.
- **Flujo principal:** recibir ruta → exigir absoluta → resolver → crear/probar → comprobar espacio → aceptar o rechazar antes de persistir.
- **Flujos alternativos:** ruta relativa, archivo, unidad inexistente o acceso denegado devuelve `invalid_path`, `access_denied` o `disk_full`.
- **Given/When/Then:** Given una ruta relativa o un archivo, When se llama `/directories/validate` o `/downloads`, Then el backend rechaza de forma estructurada. Given un renderer omite su preflight, When intenta encolar, Then el backend ejecuta el mismo contrato y no crea la tarea.
- **Prueba unitaria:** `test_relative_path_is_rejected`; `test_ensure_output_directory_rejects_existing_file`.
- **Prueba de integración:** `test_create_download_returns_structured_directory_error`.
- **Prueba E2E:** `MAN-US-004`: invocación IPC manipulada contra aplicación empaquetada.
- **Evidencia requerida:** respuesta HTTP/IPC real, ausencia del ID en SQLite y log redactado.
- **Riesgos:** enlaces simbólicos o reparse points que cambien después de validar.

## E2 — Inspección y formatos

### US-010 — Inspeccionar un enlace

- **ID:** US-010
- **Épica:** E2 — Inspección y formatos.
- **Persona:** usuario que posee autorización para guardar un medio.
- **Problema:** necesita confirmar que el enlace es válido antes de crear una descarga.
- **Precondiciones:** backend disponible; URL HTTP/HTTPS no vacía; consentimiento de cookies resuelto.
- **Flujo principal:** pega URL → pulsa Analizar → renderer invoca `inspectMedia` → backend normaliza respuesta → UI muestra medio inspeccionado.
- **Flujos alternativos:** URL inválida o excesiva se rechaza; red no disponible muestra causa y reintento; recurso no compatible no habilita la cola.
- **Given/When/Then:** Given una URL compatible, When se solicita `POST /media/inspect`, Then responde 200 con metadatos normalizados. Given URL inválida, When se inspecciona, Then no se crea descarga y se informa recuperación.
- **Prueba unitaria:** `test_inspect_media_returns_normalized_metadata`; `buildApiRequest rejects oversized inspection URLs`.
- **Prueba de integración:** `test_inspect_media_returns_normalized_metadata` ejecuta FastAPI con motor controlado.
- **Prueba E2E:** `MAN-US-010`: desde UI compilada inspeccionar el enlace controlado y comprobar tarjeta de resultado.
- **Evidencia requerida:** salida de pytest/Jest, captura o reporte E2E, respuesta redactada sin URL completa.
- **Riesgos:** disponibilidad de red y cambios externos del proveedor.

### US-011 — Mostrar metadatos suficientes

- **ID:** US-011
- **Épica:** E2 — Inspección y formatos.
- **Persona:** usuario que debe identificar el medio correcto.
- **Problema:** un enlace sin contexto puede provocar descargar contenido equivocado.
- **Precondiciones:** US-010 completada con respuesta válida.
- **Flujo principal:** la UI muestra miniatura, título, autor, duración y formatos normalizados.
- **Flujos alternativos:** campos ausentes usan valores neutros accesibles; miniatura fallida no impide continuar.
- **Given/When/Then:** Given metadatos parciales, When se normalizan, Then el contrato conserva tipos estables. Given metadatos completos, When se renderizan, Then título, autor, duración y miniatura son identificables.
- **Prueba unitaria:** `test_normalize_info_exposes_audio_and_video_presets`.
- **Prueba de integración:** `test_inspect_media_returns_normalized_metadata`.
- **Prueba E2E:** `MAN-US-011`: verificar los cinco campos en la tarjeta real inspeccionada.
- **Evidencia requerida:** JSON normalizado, consulta accesible de la UI y captura E2E.
- **Riesgos:** proveedores que omiten autor, duración o miniatura.

### US-012 — Ofrecer únicamente formatos descargables

- **ID:** US-012
- **Épica:** E2 — Inspección y formatos.
- **Persona:** usuario que elige audio, vídeo, calidad y contenedor.
- **Problema:** formatos auxiliares o no descargables generan fallos tardíos.
- **Precondiciones:** inspección válida y FFmpeg disponible cuando el formato lo requiera.
- **Flujo principal:** backend filtra formatos → normaliza presets → UI permite seleccionar uno → ID seleccionado se envía al crear descarga.
- **Flujos alternativos:** storyboard/MHTML se omiten; formato desconocido se rechaza antes de ejecutar; ausencia de formatos muestra acción sugerida.
- **Given/When/Then:** Given formatos con storyboard/MHTML, When se normalizan, Then no aparecen. Given un `format_id` desconocido, When se prepara la descarga, Then se rechaza de forma estructurada.
- **Prueba unitaria:** `test_normalize_info_omits_storyboard_and_mhtml_formats`; `test_build_command_rejects_unknown_format`.
- **Prueba de integración:** `test_inspect_media_returns_normalized_metadata`; la creación con el format_id devuelto sigue pendiente de evidencia E2E.
- **Prueba E2E:** `MAN-US-012`: seleccionar audio y vídeo reales y confirmar que la opción enviada existe en la inspección.
- **Evidencia requerida:** lista de formatos normalizada, llamada IPC y reporte de descarga por formato.
- **Riesgos:** formatos que cambian entre inspección y ejecución.

### US-013 — Explicar problemas de sesión del navegador

- **ID:** US-013
- **Épica:** E2 — Inspección y formatos.
- **Persona:** usuario que autorizó cookies de Edge o Firefox.
- **Problema:** navegador abierto, DPAPI o sesión caducada pueden impedir leer cookies.
- **Precondiciones:** consentimiento explícito activo y fuente de cookies seleccionada.
- **Flujo principal:** motor intenta leer la sesión solo durante inspección/descarga → clasifica el fallo → UI muestra causa y acción exacta.
- **Flujos alternativos:** sin consentimiento se usa `none`; navegador bloqueado solicita cerrarlo; sesión caducada solicita iniciar sesión de nuevo.
- **Given/When/Then:** Given consentimiento ausente, When se inspecciona, Then `cookie_source=none`. Given fallo DPAPI o perfil bloqueado, When responde el motor, Then el error es seguro, estructurado y accionable.
- **Prueba unitaria:** `test_build_command_uses_browser_only_when_consented`; `test_classify_error_returns_safe_actionable_codes`.
- **Prueba de integración:** `test_inspect_media_explains_locked_browser_session`; `test_inspect_media_explains_edge_dpapi_session_failure`.
- **Prueba E2E:** `MAN-US-013`: Edge abierto/cerrado, Firefox y modo sin cookies.
- **Evidencia requerida:** códigos `browser_locked`/`session_required`, copy ES/EN y logs redactados.
- **Riesgos:** cambios de cifrado del navegador y políticas de Windows.

## E3 — Cola y ejecución

### US-020 — Cola persistente

- **ID:** US-020
- **Épica:** E3 — Cola y ejecución.
- **Persona:** usuario que prepara varias descargas.
- **Problema:** necesita ordenar trabajo sin perderlo al reiniciar.
- **Precondiciones:** URL inspeccionada, formato válido y carpeta aceptada.
- **Flujo principal:** agregar a cola → persistir registro SQLite en `queued` → un único worker toma el siguiente elemento.
- **Flujos alternativos:** reinicio reencola `queued`; activo interrumpido pasa a `failed`; envío duplicado conserva IDs independientes.
- **Given/When/Then:** Given una solicitud válida, When se crea, Then devuelve ID y `queued`. Given reinicio, When carga SQLite, Then recupera pendientes una sola vez.
- **Prueba unitaria:** `test_enqueue_download`; `test_start_download_workers_starts_recovered_queue_once`.
- **Prueba de integración:** `test_download_collection_supports_queue_and_detail`; `test_load_history_applies_recovery_and_restores_waiting_queue`.
- **Prueba E2E:** `MAN-US-020`: encolar dos medios, reiniciar y verificar orden/persistencia.
- **Evidencia requerida:** filas SQLite, secuencia de estados y captura de Cola.
- **Riesgos:** cierre abrupto durante una transacción.

### US-021 — Progreso automático enriquecido

- **ID:** US-021
- **Épica:** E3 — Cola y ejecución.
- **Persona:** usuario que necesita saber el avance real.
- **Problema:** un porcentaje aislado no explica velocidad, tamaño, ETA o postprocesado.
- **Precondiciones:** descarga activa y salida de progreso del motor disponible.
- **Flujo principal:** motor emite líneas → backend normaliza porcentaje/bytes/velocidad/ETA/fase → UI refresca automáticamente.
- **Flujos alternativos:** total desconocido conserva `null`; durante FFmpeg se muestra `postprocessing`; sin tarea activa se muestra estado vacío.
- **Given/When/Then:** Given salida válida de yt-dlp, When se analiza, Then devuelve números normalizados. Given postprocesado, When el archivo aún no existe, Then no se marca `completed`.
- **Prueba unitaria:** `test_parse_progress_returns_normalized_numbers`; `test_get_progress`.
- **Prueba de integración:** `test_get_progress_endpoint`; worker en `test_worker_enters_inspecting_before_starting_external_engine`.
- **Prueba E2E:** `MAN-US-021`: observar transición y métricas sin botón manual “Check Progress”.
- **Evidencia requerida:** serie temporal de estados y aserciones de UI.
- **Riesgos:** proveedores sin tamaño total o velocidad estable.

### US-022 — Cancelar sin procesos huérfanos

- **ID:** US-022
- **Épica:** E3 — Cola y ejecución.
- **Persona:** usuario que desea detener una transferencia.
- **Problema:** cancelar solo en la UI puede dejar yt-dlp o FFmpeg ejecutándose.
- **Precondiciones:** tarea `queued`, `inspecting`, `downloading` o `postprocessing`.
- **Flujo principal:** usuario cancela por ID → backend marca cancelación → termina proceso y espera → estado `cancelled`.
- **Flujos alternativos:** si `terminate` expira se fuerza `kill`; cancelar ID inexistente devuelve error accionable; cancelar completado no borra archivo.
- **Given/When/Then:** Given proceso activo, When se cancela, Then termina y no queda huérfano. Given `terminate` bloqueado, When vence el timeout, Then se ejecuta `kill` y `wait`.
- **Prueba unitaria:** `test_download_cancellation_kills_process_if_terminate_times_out`; `test_shutdown_workers_sends_sentinel`.
- **Prueba de integración:** el endpoint de cancelación carece aún de una prueba API explícita; el gap permanece abierto.
- **Prueba E2E:** `MAN-US-022`: cancelar una descarga real y comprobar el árbol de procesos.
- **Evidencia requerida:** árbol de procesos antes/después, estado final y ausencia de archivos temporales huérfanos.
- **Riesgos:** procesos nietos creados por FFmpeg en Windows.

### US-023 — Reintentar una descarga fallida

- **ID:** US-023
- **Épica:** E3 — Cola y ejecución.
- **Persona:** usuario afectado por un fallo recuperable.
- **Problema:** repetir manualmente pierde contexto y aumenta duplicados.
- **Precondiciones:** tarea `failed` o `cancelled` con parámetros persistidos y destino nuevamente válido.
- **Flujo principal:** pulsar Reintentar → validar destino/configuración → reencolar por ID → reiniciar métricas y mantener historial coherente.
- **Flujos alternativos:** destino inválido bloquea reintento; formato retirado exige nueva inspección; tarea inexistente devuelve `not_found`.
- **Given/When/Then:** Given tarea fallida válida, When se reintenta, Then vuelve a `queued` sin duplicar registro. Given recurso irrecuperable, When se reintenta, Then conserva error accionable.
- **Prueba unitaria:** `test_retry_download_reuses_id_without_duplicate_history`.
- **Prueba de integración:** `test_retry_and_delete_download`; `test_download_actions_return_actionable_not_found`.
- **Prueba E2E:** `MAN-US-023`: inducir un fallo de red controlado y recuperar desde la interfaz.
- **Evidencia requerida:** mismo ID, secuencia `failed→queued`, un solo elemento de cola.
- **Riesgos:** duplicación si el archivo anterior existe parcialmente.

### US-024 — Registrar el archivo final real

- **ID:** US-024
- **Épica:** E3 — Cola y ejecución.
- **Persona:** usuario que espera abrir el resultado postprocesado.
- **Problema:** yt-dlp puede producir un nombre temporal diferente del MP3/MP4 final.
- **Precondiciones:** descarga completa y postprocesador configurado.
- **Flujo principal:** mantener `postprocessing` → recibir ruta final → comprobar existencia → persistir `filename` → marcar `completed`.
- **Flujos alternativos:** archivo final ausente produce `failed`; extensión inesperada se registra como salida real, no se inventa; FFmpeg fallido conserva diagnóstico.
- **Given/When/Then:** Given hook de postprocesado con ruta final, When finaliza, Then `filename` coincide con ella. Given archivo inexistente, When termina el proceso, Then no queda `completed`.
- **Prueba unitaria:** `test_worker_records_postprocessed_filename`; `test_build_command_uses_bundled_ffmpeg`.
- **Prueba de integración:** el smoke backend usa FFmpeg, pero la aserción FFprobe permanece pendiente.
- **Prueba E2E:** `MAN-US-024`: descargar audio y vídeo controlados y validar streams con FFprobe.
- **Evidencia requerida:** ruta existente, tamaño > 0, salida FFprobe y hash SHA-256.
- **Riesgos:** antivirus bloqueando renombre o archivo ocupado.

### US-025 — Apagado limpio del backend

- **ID:** US-025
- **Épica:** E3 — Cola y ejecución.
- **Persona:** usuario que cierra o reinicia la aplicación.
- **Problema:** el cierre no debe dejar backend, workers ni procesos de descarga huérfanos.
- **Precondiciones:** aplicación iniciada; cola vacía, pendiente o activa.
- **Flujo principal:** Electron solicita shutdown → backend detiene admisión → workers reciben señal → procesos hijos terminan → SQLite conserva estado recuperable → proceso sale.
- **Flujos alternativos:** cola llena usa señal de parada sin bloquear; proceso hijo resistente escala a kill; timeout registra error seguro y bloquea una salida aprobatoria.
- **Given/When/Then:** Given una cola activa, When se cierra la aplicación, Then backend, workers y procesos hijos terminan dentro del timeout. Given una cola llena, When se solicita shutdown, Then la señal se procesa sin deadlock y el estado queda recuperable.
- **Prueba unitaria:** `test_shutdown_workers_sends_sentinel`; `test_shutdown_with_full_queue`; `test_worker_consumes_sentinel_when_stopping`.
- **Prueba de integración:** `test_shutdown_endpoint`.
- **Prueba E2E:** `MAN-US-025`: cerrar la aplicación durante una transferencia y comprobar procesos y recuperación.
- **Evidencia requerida:** lista de procesos antes/después, salida del endpoint y estado SQLite ligados al mismo SHA.
- **Riesgos:** antivirus o proceso externo que ignore señales de terminación.

## E4 — Historial y archivos

### US-030 — Consultar historial persistente

- **ID:** US-030
- **Épica:** E4 — Historial y archivos.
- **Persona:** usuario que revisa resultados anteriores.
- **Problema:** necesita distinguir completados, fallidos y cancelados después de reiniciar.
- **Precondiciones:** SQLite accesible y migración inicial completada.
- **Flujo principal:** abrir Historial → listar registros persistidos → mostrar estado, título, fecha y acciones válidas.
- **Flujos alternativos:** historial vacío muestra estado vacío; JSON legado migra una vez; corrupción activa recuperación documentada.
- **Given/When/Then:** Given registros persistidos, When se reinicia, Then se listan sin duplicados. Given JSON legado, When migra dos veces, Then el resultado es idempotente y existe backup.
- **Prueba unitaria:** `test_store_round_trips_downloads`; `test_json_migration_is_idempotent_and_keeps_backup`.
- **Prueba de integración:** `test_download_collection_supports_queue_and_detail`; `test_load_history_applies_recovery_and_restores_waiting_queue`.
- **Prueba E2E:** `MAN-US-030`: completar/fallar/cancelar, reiniciar y verificar filtros.
- **Evidencia requerida:** base SQLite, backup JSON y captura del historial restaurado.
- **Riesgos:** cambios de esquema sin migración.

### US-031 — Abrir archivo completado

- **ID:** US-031
- **Épica:** E4 — Historial y archivos.
- **Persona:** usuario que quiere consumir el resultado.
- **Problema:** abrir una ruta aportada por el renderer sería inseguro.
- **Precondiciones:** registro `completed` con archivo existente dentro del destino autorizado.
- **Flujo principal:** UI envía ID → main obtiene registro confiable → valida confinamiento → usa acción nativa de Windows.
- **Flujos alternativos:** archivo ausente informa causa; ruta fuera del destino se rechaza; ID inválido no llega al sistema.
- **Given/When/Then:** Given archivo registrado dentro del destino, When se abre por ID, Then se resuelve ese archivo. Given ruta manipulada, When se intenta abrir, Then se rechaza.
- **Prueba unitaria:** `file actions resolve only recorded files inside the authorized output folder`; `file actions reject recorded paths outside the authorized output folder`.
- **Prueba de integración:** `opens completed files by download identifier instead of renderer paths`.
- **Prueba E2E:** `MAN-US-031`: abrir archivo real desde Historial en Windows.
- **Evidencia requerida:** llamada por ID, ruta resuelta redactada y proceso asociado por Windows.
- **Riesgos:** asociación de archivo inexistente en el sistema.

### US-032 — Abrir carpeta contenedora

- **ID:** US-032
- **Épica:** E4 — Historial y archivos.
- **Persona:** usuario que desea localizar el archivo.
- **Problema:** necesita llegar al destino sin exponer acceso arbitrario al filesystem.
- **Precondiciones:** registro conocido y carpeta autorizada existente.
- **Flujo principal:** UI envía ID → main valida registro → abre la carpeta contenedora.
- **Flujos alternativos:** carpeta eliminada ofrece cambiar destino; ruta fuera del alcance se rechaza.
- **Given/When/Then:** Given registro válido, When se solicita carpeta por ID, Then se abre únicamente `output_dir`. Given ID/ruta manipulada, When se solicita la acción nativa, Then no se ejecuta.
- **Prueba unitaria:** `file actions resolve only recorded files inside the authorized output folder`; `buildApiRequest rejects malformed and oversized task identifiers`.
- **Prueba de integración:** `opens completed files by download identifier instead of renderer paths` cubre archivo y carpeta por ID.
- **Prueba E2E:** `MAN-US-032`: Explorer abre el destino esperado.
- **Evidencia requerida:** ID solicitado y carpeta normalizada comprobada.
- **Riesgos:** unidad extraíble desconectada.

### US-033 — Eliminar entrada sin borrar archivo

- **ID:** US-033
- **Épica:** E4 — Historial y archivos.
- **Persona:** usuario que limpia su historial.
- **Problema:** eliminar metadatos no debe destruir contenido por accidente.
- **Precondiciones:** entrada existente en estado terminal.
- **Flujo principal:** usuario confirma eliminar entrada → backend elimina solo registro SQLite → UI actualiza lista.
- **Flujos alternativos:** ID inexistente devuelve `not_found`; tarea activa no se elimina sin cancelación; archivo permanece intacto.
- **Given/When/Then:** Given registro completado con archivo, When se elimina la entrada, Then desaparece de SQLite y el archivo sigue existiendo.
- **Prueba unitaria:** `test_delete_download_preserves_completed_file`.
- **Prueba de integración:** `test_retry_and_delete_download` cubre API, pero debe ampliarse con existencia del archivo.
- **Prueba E2E:** `MAN-US-033`: confirmar diálogo, eliminar entrada y comprobar archivo en disco.
- **Evidencia requerida:** consulta SQLite antes/después y `Test-Path` del archivo.
- **Riesgos:** confundir “eliminar historial” con “eliminar archivo”.

## E5 — Seguridad y privacidad

### US-040 — No persistir cookies ni tokens

- **ID:** US-040
- **Épica:** E5 — Seguridad y privacidad.
- **Persona:** usuario que autoriza una sesión del navegador.
- **Problema:** credenciales en logs o almacenamiento serían una fuga crítica.
- **Precondiciones:** consentimiento explícito y origen de cookies válido.
- **Flujo principal:** leer cookies únicamente durante operación → pasar origen, no contenido → redactar diagnóstico → descartar referencias sensibles.
- **Flujos alternativos:** sin consentimiento usa `none`; error de sesión no incluye secreto; exportación diagnóstica permanece redactada.
- **Given/When/Then:** Given URL/token/ruta privada en un error, When se registra, Then ninguno aparece en el log. Given cookies sin consentimiento, When se inspecciona, Then no se solicita navegador.
- **Prueba unitaria:** `test_worker_logs_do_not_expose_urls_or_private_paths`; `test_build_command_uses_browser_only_when_consented`.
- **Prueba de integración:** `does not read browser cookies before explicit consent`; `test_session_token_protects_local_api`.
- **Prueba E2E:** `MAN-US-040`: inspeccionar exportación diagnóstica con tokens señuelo.
- **Evidencia requerida:** escaneo automatizado de secretos con cero coincidencias.
- **Riesgos:** mensajes de dependencias externas no redactados.

### US-041 — Renderer con API mínima y enumerada

- **ID:** US-041
- **Épica:** E5 — Seguridad y privacidad.
- **Persona:** usuario protegido frente a contenido renderer comprometido.
- **Problema:** un puente IPC genérico permitiría operaciones arbitrarias.
- **Precondiciones:** `contextIsolation=true`, `nodeIntegration=false`, preload cargado y CSP activa.
- **Flujo principal:** React llama método enumerado → preload congela API → main valida operación/payload/sender → backend recibe contrato acotado.
- **Flujos alternativos:** operación desconocida, ID malformado o URL excesiva se rechazan antes de I/O.
- **Given/When/Then:** Given operación no declarada, When se invoca, Then lanza `Unsupported operation`. Given sender/payload no confiable, When intenta invocar IPC, Then no alcanza backend ni filesystem.
- **Prueba unitaria:** suite `ipc-contract.test.js`, especialmente operaciones declaradas e IDs acotados.
- **Prueba de integración:** `electron-security.test.js` cubre sender/main frame, preferencias endurecidas y navegación.
- **Prueba E2E:** `MAN-US-041`: comprobar ausencia de `require`, Node y navegación externa desde renderer.
- **Evidencia requerida:** configuración BrowserWindow, CSP, pruebas de abuso y resultado negativo.
- **Riesgos:** nuevos canales IPC añadidos sin contrato.

### US-042 — Backend exclusivamente loopback

- **ID:** US-042
- **Épica:** E5 — Seguridad y privacidad.
- **Persona:** usuario cuyo motor local no debe exponerse a la red.
- **Problema:** escuchar en interfaces públicas permitiría control remoto.
- **Precondiciones:** Electron inicia backend con puerto dinámico y token de sesión.
- **Flujo principal:** seleccionar puerto libre → escuchar `127.0.0.1` → inyectar token al main → renderer nunca conoce acceso genérico.
- **Flujos alternativos:** puerto ocupado se reemplaza; token incorrecto devuelve 401; backend caído se reinicia o muestra motor no disponible.
- **Given/When/Then:** Given petición sin token, When llega a API protegida, Then responde 401. Given proceso iniciado, When se inspeccionan sockets, Then solo existe listener loopback.
- **Prueba unitaria:** `test_session_token_protects_local_api`.
- **Prueba de integración:** no existe aún una prueba empaquetada que inspeccione dirección y puerto del listener.
- **Prueba E2E:** `MAN-US-042`: comprobar que el backend no escucha en interfaces públicas.
- **Evidencia requerida:** socket local, puerto dinámico y respuestas 401/200 con token incorrecto/correcto.
- **Riesgos:** configuración accidental de Uvicorn en `0.0.0.0`.

### US-043 — Diagnósticos locales y redactados

- **ID:** US-043
- **Épica:** E5 — Seguridad y privacidad.
- **Persona:** usuario/soporte que necesita diagnosticar sin filtrar datos.
- **Problema:** logs ilimitados o sensibles comprometen privacidad y disco.
- **Precondiciones:** logging local configurado y exportación solo por acción explícita.
- **Flujo principal:** registrar códigos/eventos mínimos → rotar archivos → redactar secretos/URLs/rutas → exportar bajo solicitud.
- **Flujos alternativos:** fallo de escritura no bloquea descarga; exportación cancelada no crea paquete; caracteres de control se eliminan.
- **Given/When/Then:** Given datos sensibles en excepción, When se registra/exporta, Then se reemplazan. Given logs superan límite, When se escribe el siguiente evento, Then rotan sin borrar descargas.
- **Prueba unitaria:** `test_worker_logs_do_not_expose_urls_or_private_paths`; `notifications are bounded and stripped of control characters`.
- **Prueba de integración:** `test_logging_uses_data_directory_and_redacts_sensitive_values`, `diagnostics.test.js` y acción UI de exportación.
- **Prueba E2E:** `MAN-US-043`: exportar diagnóstico y escanear secretos señuelo.
- **Evidencia requerida:** paquete exportado, tamaños de rotación y resultado del escáner.
- **Riesgos:** stack traces de terceros con rutas privadas.

## E6 — Distribución comercial open source

### US-050 — Instalar sin Python ni Node externos

- **ID:** US-050
- **Épica:** E6 — Distribución comercial.
- **Persona:** cliente con un Windows limpio.
- **Problema:** el producto no puede depender de herramientas de desarrollo instaladas.
- **Precondiciones:** NSIS incluye backend PyInstaller, yt-dlp, FFmpeg/FFprobe y runtime JavaScript requerido.
- **Flujo principal:** instalar por usuario → iniciar Electron → health check backend/motor → inspeccionar y descargar.
- **Flujos alternativos:** recurso empaquetado ausente bloquea release con diagnóstico; instalación previa se actualiza conservando datos.
- **Given/When/Then:** Given Windows sin Python/Node, When instala e inicia, Then backend y motor funcionan. Given recurso requerido ausente, When se ejecuta smoke, Then release falla antes de publicar.
- **Prueba unitaria:** `test_build_command_uses_bundled_node_runtime`; `uses the packaged Node runtime instead of a machine installation`.
- **Prueba de integración:** la construcción NSIS existe, pero la ejecución en VM limpia permanece pendiente.
- **Prueba E2E:** `MAN-US-050`: instalación limpia Windows 10/11, audio y vídeo reales sin runtimes externos.
- **Evidencia requerida:** inventario previo de software, log de instalación, health check y archivos reproducibles.
- **Riesgos:** falta ejecutar la matriz final en una VM sin Node/Python instalados.

### US-051 — Actualización verificada

- **ID:** US-051
- **Épica:** E6 — Distribución comercial.
- **Persona:** cliente que necesita correcciones sin reinstalar manualmente.
- **Problema:** actualizar binarios sin verificar permite corrupción o sustitución.
- **Precondiciones:** versión publicada con manifiesto y SHA-256; canal configurable; descarga activa protegida.
- **Flujo principal:** comprobar cada 24 h → descargar temporal → verificar hash → health check → promover atómicamente → avisar cuando sea seguro.
- **Flujos alternativos:** checksum inválido no reemplaza; red caída no bloquea uso; descarga activa pospone reinicio.
- **Given/When/Then:** Given hash correcto, When instala motor, Then conserva versión previa y promueve nueva. Given descarga activa, When llega actualización de app, Then no solicita reinicio inmediato.
- **Prueba unitaria:** `test_parse_sha256_finds_exact_windows_asset`; `application updates wait for active downloads`.
- **Prueba de integración:** `test_install_verified_promotes_binary_and_keeps_previous`.
- **Prueba E2E:** `MAN-US-051`: actualización N→N+1 y health check con artefactos aprobados.
- **Evidencia requerida:** hashes origen/destino, versiones, registro del health check.
- **Riesgos:** disponibilidad del canal de publicación y ataques a la cadena de suministro.

### US-052 — Rollback después de actualización fallida

- **ID:** US-052
- **Épica:** E6 — Distribución comercial.
- **Persona:** cliente que debe conservar una versión utilizable.
- **Problema:** una actualización defectuosa no puede inutilizar la aplicación.
- **Precondiciones:** versión anterior preservada y operaciones de reemplazo atómicas.
- **Flujo principal:** fallo de checksum/health check → descartar candidata → restaurar/conservar anterior → registrar código seguro → continuar.
- **Flujos alternativos:** rollback también fallido detiene nuevas descargas pero conserva datos; reintento se limita por intervalo.
- **Given/When/Then:** Given checksum incorrecto, When se instala, Then actual permanece intacta. Given intento fallido reciente, When se vuelve a comprobar, Then no entra en bucle.
- **Prueba unitaria:** `test_install_verified_rejects_checksum_and_preserves_current`; `test_failed_update_is_not_retried_again_within_interval`.
- **Prueba de integración:** `test_install_verified_rejects_checksum_and_preserves_current`; el roll-forward de aplicación NSIS permanece pendiente.
- **Prueba E2E:** `MAN-US-052`: actualización deliberadamente rota y arranque de versión anterior.
- **Evidencia requerida:** hashes antes/después, versión activa, logs y datos de usuario preservados.
- **Riesgos:** antivirus bloqueando reemplazo atómico.

### US-053 — Instalador firmado y reproducible

- **ID:** US-053
- **Épica:** E6 — Distribución comercial.
- **Persona:** publicador y cliente que verifican procedencia.
- **Problema:** un instalador no firmado genera advertencias y no demuestra autenticidad.
- **Precondiciones:** versión/tag inmutable, dependencias bloqueadas, licencias revisadas y certificado Authenticode válido.
- **Flujo principal:** checkout limpio → pruebas → build backend/UI → NSIS → firma/timestamp → hash → checklist → publicación.
- **Flujos alternativos:** sin certificado se etiqueta build interna y se prohíbe publicación pública; diferencia no explicada entre builds bloquea release.
- **Given/When/Then:** Given certificado válido, When se firma, Then `Get-AuthenticodeSignature` devuelve `Valid`. Given certificado ausente, When se construye, Then el artefacto no se declara release pública.
- **Prueba unitaria:** no aplica a la criptografía del sistema; la validación de configuración de firma permanece pendiente.
- **Prueba de integración:** el build NSIS está cubierto parcialmente; la firma actual no es válida y el criterio no está cumplido.
- **Prueba E2E:** `MAN-US-053`: instalar, actualizar y desinstalar el artefacto firmado en VM limpia.
- **Evidencia requerida:** firma válida, timestamp, SHA-256, SBOM/avisos y checklist firmado.
- **Riesgos:** certificado Authenticode normalmente tiene coste; contradicción con coste cero debe resolverse mediante certificado donado/patrocinado o distribución abierta no firmada.

### US-054 — Desinstalar conservando descargas

- **ID:** US-054
- **Épica:** E6 — Distribución comercial open source.
- **Persona:** cliente que retira la aplicación sin perder sus medios.
- **Problema:** el desinstalador no debe borrar descargas ni datos fuera del directorio instalado.
- **Precondiciones:** aplicación instalada mediante el NSIS exacto y al menos un archivo de usuario existente.
- **Flujo principal:** cerrar procesos → ejecutar desinstalación por usuario → eliminar binarios y accesos de la aplicación → conservar carpeta de descargas y archivos producidos.
- **Flujos alternativos:** proceso activo bloquea desinstalación con acción clara; ruta personalizada conserva archivos; configuración se elimina solo mediante una opción explícita.
- **Given/When/Then:** Given un archivo descargado antes de desinstalar, When se ejecuta el desinstalador, Then el archivo permanece idéntico y los binarios se eliminan. Given una descarga activa, When se solicita desinstalar, Then se detiene de forma segura antes de modificar archivos instalados.
- **Prueba unitaria:** no aplica al contrato NSIS; la comprobación requiere el instalador exacto.
- **Prueba de integración:** no existe aún una prueba instalada automatizada; el caso manual US-054 permanece pendiente y bloquea aceptación.
- **Prueba E2E:** `MAN-US-054`: desinstalar el NSIS exacto y comparar el hash del archivo de usuario antes/después.
- **Evidencia requerida:** hash del instalador, comandos de desinstalación, hash del archivo preservado y ausencia de procesos.
- **Riesgos:** reglas NSIS demasiado amplias o carpeta de destino dentro del directorio de instalación.

## E7 — Experiencia accesible y localizada

### US-060 — Operar con accesibilidad de Windows

- **ID:** US-060
- **Épica:** E7 — Experiencia accesible y localizada.
- **Persona:** usuario que navega con teclado, lector de pantalla, escalado o movimiento reducido.
- **Problema:** las acciones críticas deben ser perceptibles y operables sin ratón ni animación obligatoria.
- **Precondiciones:** aplicación iniciada con preferencias de accesibilidad de Windows disponibles.
- **Flujo principal:** navegar por foco lógico → identificar nombres, roles y estados → activar controles con teclado → recibir errores y progreso anunciados.
- **Flujos alternativos:** escala 150 % conserva contenido; movimiento reducido elimina transiciones no esenciales; foco nunca queda atrapado.
- **Given/When/Then:** Given navegación solo por teclado, When recorre Nueva descarga, Cola, Historial y Ajustes, Then cada control es alcanzable y muestra foco visible. Given movimiento reducido o escala 150 %, When cambia el estado de una transferencia, Then el contenido permanece legible y funcional.
- **Prueba unitaria:** las pruebas React actuales verifican flujos, pero no cubren aún auditoría AA, lector de pantalla ni foco completo.
- **Prueba de integración:** no existe aún automatización de accesibilidad empaquetada; el caso manual US-060 permanece pendiente y bloquea aceptación.
- **Prueba E2E:** `MAN-US-060`: ejecutar teclado, lector, contraste y escalas 100/125/150 %.
- **Evidencia requerida:** reporte de accesibilidad, secuencia de foco, escala, SO, ejecutor, fecha y capturas.
- **Riesgos:** controles personalizados sin nombre accesible o reflow insuficiente.

### US-061 — Interfaz completa en español e inglés

- **ID:** US-061
- **Épica:** E7 — Experiencia accesible y localizada.
- **Persona:** usuario que selecciona español o inglés.
- **Problema:** navegación, estados, acciones y errores no deben mezclar idiomas ni perder significado.
- **Precondiciones:** catálogos ES/EN cargados y preferencia persistente disponible.
- **Flujo principal:** abrir Ajustes → cambiar idioma → actualizar toda la UI → persistir selección → conservarla tras reinicio.
- **Flujos alternativos:** clave ausente bloquea el gate en lugar de mostrar texto interno; error backend se traduce por código estructurado.
- **Given/When/Then:** Given español predeterminado, When inicia por primera vez, Then navegación y errores visibles están en español. Given inglés seleccionado, When reinicia, Then toda la interfaz permanece en inglés sin claves crudas.
- **Prueba unitaria:** `shows Spanish navigation and no manual progress control`; `changes the interface language from settings`.
- **Prueba de integración:** los flujos React cubren cambio y persistencia visible; falta auditoría exhaustiva de catálogos y errores empaquetados.
- **Prueba E2E:** `MAN-US-061`: recorrer todos los estados en ES/EN y escanear claves o idioma mezclado.
- **Evidencia requerida:** catálogo comparado, capturas por estado, preferencia persistida, SO, ejecutor, fecha y SHA.
- **Riesgos:** copy nuevo sin clave equivalente o contenido técnico sin traducción.
