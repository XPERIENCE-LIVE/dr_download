# ADR-004 — Reproducción en streaming y listas de reproducción

**Estado:** aprobado por producto el 2026-10-11; implementación y aceptación tienen estados separados. La publicación firmada de esta función permanece bloqueada hasta revisar las condiciones de SignPath Foundation y de la distribución pública.

**Contexto:** el usuario quiere ver vídeos de YouTube y Vimeo dentro de la aplicación sin los anuncios que inyecta el reproductor oficial, saltar los patrocinios grabados por el creador y organizar listas propias o importadas. El [alcance](../../product/scope.md) excluía el streaming y exige un ADR, impacto en seguridad/privacidad e historias antes de tocar código.

**Decisión:** aplicar el [contrato de reproducción y listas](../../product/playback-and-playlists.md) mediante US-067–US-072 (épica E8).
- El único motor sigue siendo `yt-dlp.exe` incluido (ADR-001): resuelve los streams y las entradas de listas. Nunca se importa yt-dlp como biblioteca.
- La ausencia de anuncios es consecuencia del diseño: los anuncios los inserta el reproductor oficial y no forman parte de los streams resueltos. No se añade un bloqueador ni se manipula tráfico de terceros.
- El backend combina vídeo y audio con el FFmpeg incluido (`-c copy`, MP4 fragmentado) y lo entrega por `StreamingResponse`. Las URLs de stream, sus cabeceras y el token de sesión nunca llegan al renderer.
- Electron entrega el medio al renderer mediante el esquema privilegiado `dr-stream:`; la CSP solo añade `media-src 'self' dr-stream:`. Se mantienen `connect-src 'none'`, `frame-src 'none'`, navegación bloqueada y ningún reproductor embebido ni iframe de terceros.
- Buscar dentro del vídeo reinicia la combinación en el desplazamiento solicitado; no se emula un archivo completo ni se cachea el medio en disco.
- Los patrocinios se saltan con segmentos de SponsorBlock, desactivado por defecto, con consentimiento propio, persistido y revocable. Si no hay segmentos o el servicio falla, la reproducción continúa y la interfaz lo indica.
- La sesión con navegador reutiliza el consentimiento estricto existente por fuente; la reproducción revalida esa autorización como inspección y descarga.
- Las listas son locales (SQLite) y pueden importarse desde un enlace de lista con `--flat-playlist`, con límite de 500 entradas.

**Riesgos aceptados por producto:**
- Reproducir YouTube fuera de su reproductor y sin anuncios incumple sus Términos de Servicio. Es un riesgo contractual con la plataforma, no elusión de DRM. Dr. Download sigue sin eludir DRM: un formato protegido o una emisión en directo se rechazan con causa y recuperación.
- Usar cookies de una cuenta desde un cliente no oficial puede provocar que el proveedor limite o marque esa cuenta. El consentimiento lo advierte.
- SponsorBlock es un servicio de terceros que recibe la IP del equipo y un prefijo de 4 caracteres del SHA-256 del identificador del vídeo.
- Los proveedores cambian sus clientes con frecuencia; las URLs caducan y están ligadas a la IP. La reproducción depende de actualizar el motor igual que la descarga.

**Consecuencias:** se añaden rutas API de reproducción y listas, operaciones IPC enumeradas, un esquema de protocolo y tablas SQLite. No se añaden dependencias de runtime: `httpx`, FFmpeg, Node y yt-dlp ya forman parte del producto. La inspección deja de bloquear el event loop porque un stream activo no puede congelarse mientras se analiza otro enlace. Cada proceso de reproducción tiene dueño y se termina al desconectar, buscar o cerrar.

**Diferido:** reordenar ítems de una lista, reproducción aleatoria, emisiones en directo, Picture-in-Picture y descargar una lista completa; se registran en el [backlog](../../product/backlog.md). Importar una lista **no** levanta el diferimiento de «pegar varios enlaces». Biblioteca multimedia, edición, cuentas y nube permanecen fuera de alcance.
