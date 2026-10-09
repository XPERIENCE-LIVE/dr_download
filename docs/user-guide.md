# Guía de uso / User guide

## Español

Instala Dr. Download y ábrelo directamente en Windows. No necesitas una máquina virtual, Docker, Python ni Node instalados por separado. El primer inicio necesita Internet para obtener y verificar el motor de descarga si aún no está disponible. Las referencias a «VM limpia» en las pruebas describen un entorno de validación, no un requisito de uso.

1. Abre **Nueva descarga**, pega el enlace y pulsa **Analizar enlace**.
2. Si el contenido requiere sesión, elige Edge o Firefox, autoriza el uso temporal y cierra el navegador completamente.
3. Elige **Vídeo compatible** (MP4 H.264/AAC), **Mejor vídeo** o **Audio MP3** y carpeta. **Formatos avanzados** incluye audio original y streams individuales. Si falta tamaño, se indica **Tamaño desconocido**; una estimación no garantiza el tamaño final.
4. Pulsa **Agregar a la cola** y espera confirmación; después usa **Ver cola**. La inspección muestra actividad sin porcentaje; el encolado tiene estado propio. No es necesario actualizar manualmente el progreso.
5. Al finalizar, abre el archivo o su carpeta desde **Historial**.

Si falla la inspección, comprueba que el enlace se reproduce en el navegador elegido, que este esté cerrado y que exista conexión. Dr. Download no guarda tus cookies.

Puedes visitar Cola, Historial o Ajustes y volver a Nueva descarga sin perder enlace, inspección ni selección mientras la aplicación siga abierta. Cambiar el enlace requiere analizar de nuevo; el borrador no se conserva tras cerrar.

Historial permite buscar por título, enlace o nombre de archivo y filtrar por estado. Limpia los filtros para ver todo. Un aviso indica enlaces exactos ya cargados en cola/historial; puedes repetirlos si lo necesitas y la protección de archivos sigue activa. URLs equivalentes pueden no generar aviso.

Ajustes muestra **Guardando**, confirmación o fallo. Ante un fallo, reintenta y espera confirmación. El uso de cookies no se autoriza si guardar el consentimiento falla; puedes usar modo sin cookies. Revoca el consentimiento desde Ajustes para impedir nuevas operaciones con cookies; una descarga ya iniciada puede continuar.

Cada navegador necesita autorización propia: cambiar de Edge a Firefox requiere consentir de nuevo. La cola y los reintentos consultan el permiso guardado actual y pasan a modo sin cookies tras revocación confirmada. Si guardar la revocación falla, las nuevas inspecciones y descargas con navegador quedan bloqueadas en la interfaz; reintenta el guardado para que el cambio también aplique al servicio y tras reiniciar. Puedes navegar y volver a Ajustes sin perder el resultado de un guardado pendiente.

Los errores incluyen causa y acción: volver a analizar, reintentar tarea, elegir carpeta, revisar Ajustes o exportar diagnóstico local. Reintentar tarea conserva su ID. Si el servicio local está desconectado, reintenta o reinicia; reiniciar descarta el borrador. El preset compatible falla explícitamente si el origen no ofrece los codecs requeridos; puedes elegir otro resultado conscientemente.

## English

Install Dr. Download and open it directly on Windows. No virtual machine, Docker, separately installed Python or Node is required. First launch needs Internet to obtain and verify the download engine if it is not already available. A “clean VM” is a test environment, not a requirement for using the application.

1. Open **New download**, paste the link and select **Inspect link**.
2. If a session is required, choose Edge or Firefox, allow temporary access and close the browser completely.
3. Choose **Compatible video** (H.264/AAC MP4), **Best video** or **MP3 audio** and destination. **Advanced formats** contains original audio and individual streams. Missing estimates show **Size unknown**; estimates do not guarantee final size.
4. Select **Add to queue**, wait for confirmation and use **View queue**. Inspection shows activity without a percentage; queueing has its own pending state. Progress updates automatically.
5. Open the completed file or folder from **History**.

Only download content you are authorized to save.

Navigate to Queue, History or Settings and return without losing your link, inspection or selection during this session. Editing the link requires another inspection; closing the application discards the draft.

Search History by title, link or filename and filter by state. Clear filters to see all entries. A warning identifies exact links already loaded in the queue/history; you may repeat them intentionally, with file protection retained. Equivalent URLs may not trigger a warning.

Settings shows saving, confirmation or failure. Retry a failed save and wait for confirmation. Failed consent persistence does not authorize browser access; cookie-free mode remains available. Revoke consent in Settings to prevent new cookie-enabled operations; an existing transfer may continue.

Each browser needs its own permission: switching from Edge to Firefox requires fresh consent. Queued tasks and retries use the current saved permission and switch to no cookies after confirmed revocation. If saving revocation fails, the interface blocks new browser-enabled inspection/download requests; retry saving so the change also applies to the local service and after restart. Navigate away and return to Settings without losing a pending save result.

Errors explain the cause and next action: inspect again, retry a task, choose a folder, review Settings or export local diagnostics. Retrying retains the task ID. If the local service is disconnected, retry or restart; restarting discards the draft. Compatible video fails explicitly when required codecs are unavailable; choose another result consciously.
# Carpeta de destino

Al iniciar, Dr. Download crea y valida `Descargas\\Dr. Download`. Si Windows no permite escribir en la carpeta elegida, la descarga no se encola: usa “Usar carpeta Descargas” o selecciona otra ubicación. El enlace inspeccionado se conserva.

La aplicación requiere al menos 128 MiB o el doble del tamaño estimado, lo que sea mayor, para permitir descarga y procesamiento. Sin estimación usa el mínimo; el espacio puede cambiar y un fallo posterior exige liberar espacio o elegir otra carpeta.

The default Downloads/Dr. Download folder is created and checked before queueing. Admission requires at least 128 MiB or twice the advisory estimate, whichever is larger. Unknown estimates use the minimum; space can still change later. Choose another folder or free space when prompted.

