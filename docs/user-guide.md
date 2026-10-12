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

### Reproducción y listas

Disponible en el código de la rama de reproducción; la aceptación del instalador Windows 10/11 sigue pendiente. No se carga el reproductor oficial ni sus anuncios. Las promociones grabadas en el propio vídeo pueden permanecer. Reproducir YouTube fuera de su reproductor incumple sus Términos de Servicio y usar cookies de tu cuenta puede provocar restricciones. DRM y emisiones en directo se rechazan; un proveedor puede exigir sesión o impedir extraer un vídeo.

1. Abre **Reproductor**, pega un enlace individual de YouTube o Vimeo y pulsa **Reproducir**. También puedes pulsar **Reproducir** después de analizar el vídeo en Nueva descarga.
2. Elige la calidad máxima para el próximo vídeo (480p, 720p o 1080p). El reproductor muestra la altura que realmente pudo resolver.
3. Usa **Pausar/Continuar**, **Silenciar/Activar sonido** y **Pantalla completa**. La barra de **Posición** busca sobre la duración total; admite fracciones de segundo. Buscar estando en pausa conserva la pausa. Si no se conoce la duración, no hay barra de búsqueda.
4. Si caduca la sesión o el medio falla, revisa la causa y pulsa **Volver a cargar**. **Cerrar reproductor** detiene la sesión; navegar a Ajustes o Listas la conserva.

Para saltar promociones, lee el aviso de SponsorBlock en Ajustes y pulsa **Autorizar SponsorBlock y guardar**. El servicio recibe tu IP y un prefijo del hash del identificador de YouTube. La autorización solo se activa después de guardarse; puedes revocarla por separado de las cookies. **Patrocinio omitido** ofrece **Deshacer salto** para ver ese segmento. Si el servicio falla, se muestra el aviso y el vídeo sigue sin saltos; los segmentos dependen de datos de la comunidad.

En **Listas**, escribe un nombre y pulsa **Crear lista**. Selecciona la lista, pega un enlace y pulsa **Añadir a lista**; el mismo botón está disponible después de analizar un vídeo y conserva sus metadatos. Un aviso permite repetir un enlace intencionalmente. **Guardar nombre** confirma un renombrado; **Eliminar** quita una entrada y **Borrar lista** pide confirmación. No se borran archivos descargados.

Pega un enlace de lista en **Enlace de lista** y pulsa **Importar lista** para crear una nueva lista local, hasta 500 entradas. El resumen cuenta las importadas y no disponibles; estas permanecen marcadas. **Cancelar importación** impide el guardado si la operación aún no hizo commit; nunca se guarda una lista parcial. Si ya terminó, la interfaz muestra que tu lista está disponible en lugar de afirmar que se canceló. **Reproducir lista** mantiene el orden, permite **Anterior/Siguiente**, avisa con nombre y causa si omite un vídeo y se detiene al final. Las listas persisten tras reiniciar; las sesiones de reproducción se vuelven a resolver.

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

### Playback and playlists

Available in the playback feature branch source; installed-Windows 10/11 acceptance is still pending. The official player and its ads are not loaded. Promotions recorded inside a video may remain. Playing YouTube outside its player breaches its Terms of Service and using account cookies may lead to restrictions. DRM and live streams are rejected; a provider may require a session or prevent extraction.

1. Open **Player**, paste an individual YouTube or Vimeo link and select **Play**. You can also select **Play** after inspecting a video in New download.
2. Choose the maximum quality for the next video (480p, 720p or 1080p). The player shows the actual height that could be resolved.
3. Use **Pause/Resume**, **Mute/Unmute** and **Full screen**. **Position** seeks across the source duration and accepts fractional seconds. Seeking while paused keeps playback paused. Unknown duration hides the seek bar.
4. If the session expires or media fails, read the cause and select **Reload**. **Close player** stops the session; navigating to Settings or Playlists keeps it.

For sponsor skipping, read the SponsorBlock notice in Settings and select **Allow SponsorBlock and save**. The service receives your IP and a prefix of the YouTube video ID hash. Permission starts only after a successful save and is revoked separately from browser cookies. **Sponsor skipped** offers **Undo skip** to watch that segment. Service failure displays a warning and the video continues without skips; segment coverage depends on community data.

In **Playlists**, enter a name and select **Create list**. Choose a list, paste a link and select **Add to list**; the same action after inspection preserves the video metadata. A warning permits intentional duplicate links. **Save name** confirms a rename; **Remove** deletes an entry and **Delete list** requires confirmation. Downloaded files are kept.

Paste a **Playlist link** and select **Import list** to create a local list with up to 500 entries. The summary counts imported and unavailable entries; unavailable entries stay marked. **Cancel import** prevents saving before commit and partial lists are never saved. If the import already finished, the interface reports that your list is available instead of claiming cancellation. **Play list** preserves order, offers **Previous/Next**, names and explains skipped videos and stops at the end. Lists persist after restart; playback sessions are resolved again.
# Carpeta de destino

Al iniciar, Dr. Download crea y valida `Descargas\\Dr. Download`. Si Windows no permite escribir en la carpeta elegida, la descarga no se encola: usa “Usar carpeta Descargas” o selecciona otra ubicación. El enlace inspeccionado se conserva.

La aplicación requiere al menos 128 MiB o el doble del tamaño estimado, lo que sea mayor, para permitir descarga y procesamiento. Sin estimación usa el mínimo; el espacio puede cambiar y un fallo posterior exige liberar espacio o elegir otra carpeta.

The default Downloads/Dr. Download folder is created and checked before queueing. Admission requires at least 128 MiB or twice the advisory estimate, whichever is larger. Unknown estimates use the minimum; space can still change later. Choose another folder or free space when prompted.

