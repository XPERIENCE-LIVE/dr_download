# Alcance del producto

## Scope-in de esta versión

- Aplicación de escritorio Windows 10/11 x64.
- Descargas individuales y cola persistente con una ejecución simultánea.
- Inspección de metadatos y formatos antes de encolar.
- Audio/vídeo mediante yt-dlp y FFmpeg incluidos en el paquete.
- Historial SQLite, cancelación, reintento y acciones para abrir archivo/carpeta.
- Español predeterminado e inglés seleccionable.
- Cookies de Edge, Firefox y modo sin cookies con consentimiento explícito.
- Actualización verificable del motor y de la aplicación.
- Diagnósticos locales, rotativos y exportables por acción del usuario.
- Experiencia confiable US-062–US-066: estado veraz, borrador de sesión, presets simples y avanzados, espacio estimado, errores ES/EN, guardado y consentimiento revocable.
- Búsqueda local de historial por título/URL/archivo, filtro por estado y aviso no prohibitivo de enlace repetido; aprobados mediante ADR-003.
- Reproducción en streaming dentro de la aplicación de enlaces individuales de YouTube y Vimeo sin el reproductor oficial ni sus anuncios, búsqueda dentro del vídeo, salto opcional de patrocinios con consentimiento propio, listas locales e importación de listas por enlace (US-067–US-072); aprobados mediante ADR-004 y definidos en el [contrato de reproducción](playback-and-playlists.md).

## Scope-out explícito

- Cuentas, nube, sincronización, pagos, licencias comerciales y telemetría.
- Biblioteca multimedia, edición de vídeo, emisiones en directo, DRM bypass o extracción de contenido no autorizado. La reproducción aprobada por ADR-004 no convierte las listas en biblioteca ni cachea medios en disco.
- macOS, Linux, ARM y versiones móviles.
- Servicio SaaS o backend remoto.
- Soporte garantizado para contenido bloqueado por políticas externas de YouTube.
- Pegado múltiple, reordenar cola, pausa/reanudación real, IA y reescritura; razones y condiciones en el [backlog diferido](backlog.md).

## Cambios de alcance

Cualquier solicitud fuera de `scope-in` requiere un ADR, impacto en seguridad/privacidad, nuevas historias y actualización de la matriz de aceptación antes de tocar código.
