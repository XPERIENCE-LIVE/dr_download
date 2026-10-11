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

## Scope-out explícito

- Cuentas, nube, sincronización, pagos, licencias comerciales y telemetría.
- Biblioteca multimedia, edición de vídeo, streaming, DRM bypass o extracción de contenido no autorizado.
- macOS, Linux, ARM y versiones móviles.
- Servicio SaaS o backend remoto.
- Soporte garantizado para contenido bloqueado por políticas externas de YouTube.
- Pegado múltiple, reordenar cola, pausa/reanudación real, IA y reescritura; razones y condiciones en el [backlog diferido](backlog.md).

## Cambios de alcance

Cualquier solicitud fuera de `scope-in` requiere un ADR, impacto en seguridad/privacidad, nuevas historias y actualización de la matriz de aceptación antes de tocar código.
