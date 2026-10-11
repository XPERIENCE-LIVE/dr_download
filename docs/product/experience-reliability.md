# Experiencia confiable — contrato de implementación

Decisión de producto aprobada el 2026-10-08. Las historias US-062–US-066 están `partial`: describen el comportamiento exigido, no certifican su aceptación. La [matriz de aceptación](acceptance-matrix.md), la [trazabilidad](../qa/traceability-matrix.md) y los casos manuales conservan los gaps de evidencia. La expansión está aprobada en [ADR-003](../architecture/adr/ADR-003-experience-and-history.md).

## Estado y continuidad — US-062

- El backend aparece disponible solo tras una lectura confirmada. Antes de resolver una lectura muestra comprobación; ante fallo muestra desconexión y recuperación. La presencia del puente IPC no confirma disponibilidad. Un fallo de escritura no implica por sí solo pérdida de conectividad.
- La inspección es una operación indeterminada con indicador ocupado y anuncio accesible; no inventa porcentaje, velocidad ni ETA. Encolar tiene su propio estado y acción deshabilitada mientras se confirma la creación de una sola tarea.
- El pie muestra primero la tarea que está `inspecting`, `downloading` o `postprocessing`; solo muestra una tarea `queued` cuando no hay ejecución. Las fases son etiquetas ES/EN y los valores desconocidos no son cero.
- El borrador de Nueva descarga conserva enlace, inspección, formato y destino al navegar por la aplicación. Vive solo durante la sesión: no se guarda automáticamente en disco y un reinicio puede descartarlo. Editar el enlace invalida los metadatos previos. Tras encolar, **Ver cola / View queue** es una acción explícita.

## Elegir un resultado — US-063

| Preset | Promesa visible | Contrato |
|---|---|---|
| `video-compatible` | Vídeo compatible / Compatible video | MP4 con H.264 y AAC; si no están disponibles se rechaza con recuperación, sin sustituir codecs |
| `video-best` | Mejor vídeo / Best video | Mejor combinación disponible; la descripción advierte que puede requerir otro reproductor |
| `audio-mp3` | Audio MP3 / MP3 audio | Conversión MP3 mediante FFmpeg incluido |
| `audio-original` | Audio original / Original audio | Opción avanzada; conserva el formato de origen |
| streams individuales | Formatos avanzados / Advanced formats | Identificadores técnicos bajo expansión explícita; excluir storyboard/MHTML |

No prometer compatibilidad por usar únicamente una extensión `.mp4`. Un stream de vídeo o audio aislado se identifica como tal. La duración, calidad y tamaño se presentan con nombres comprensibles; tamaño ausente significa **Tamaño desconocido / Size unknown**, nunca `0 B` ni una estimación fabricada.

La estimación `estimated_bytes` es asesoría de la inspección, no una garantía de descarga ni un permiso. El renderer compara el umbral con el espacio libre devuelto al validar carpeta y envía la estimación al crear la tarea; IPC y API admiten omisión/null o un entero estricto no negativo dentro del límite compartido documentado en el contrato API. Se rechazan booleanos, fracciones, cadenas y valores fuera de rango. Al crear tarea, el backend mantiene la escritura de prueba, permisos y validación de ruta y exige espacio libre de al menos `max(128 * 1024 * 1024, 2 * estimated_bytes)`; sin estimación exige el mínimo. Las opciones y metadatos se siguen validando en backend. El espacio puede cambiar después del preflight y un fallo posterior conserva un error accionable.

## Causa y recuperación — US-064

Todo fallo visible incluye causa comprensible y siguiente acción traducidas por código estable, sin mostrar excepciones crudas, tokens, cookies, enlaces privados o rutas sensibles. Consultar [copy de errores](../design/error-copy.md). Un código desconocido produce un mensaje humano seguro y acceso a diagnóstico local redactado.

Las acciones reflejan la operación: reintentar una tarea conserva su ID; volver a analizar conserva el enlace; problemas de cookies dirigen a consentimiento/Ajustes o modo sin cookies; problemas de destino permiten elegir carpeta; fallos internos permiten exportar diagnóstico. No iniciar silenciosamente operaciones ni atribuir un error de formato a permisos.

Los fallos atraviesan IPC y contextBridge como rechazo simple `{ message, detail }`; consumidores acceden a `reason.detail` sin asumir instancia `Error`. Un código desconocido muestra causa/recuperación segura localizada y conserva el detalle estructurado para diagnóstico.

## Guardar preferencias y consentir — US-065

- Una escritura de ajustes presenta estado pendiente, éxito solo tras confirmación y fallo visible con reintento. Un fallo no muestra confirmación ficticia ni deja la aplicación creyendo que el valor está persistido.
- Consentir lectura temporal de Edge/Firefox requiere confirmación persistida. Si guardar el consentimiento falla, la inspección con cookies no se ejecuta y el usuario puede reintentar o usar modo sin cookies.
- Ajustes permite revocar consentimiento; se persiste el rechazo y las nuevas operaciones no pueden usar cookies hasta autorizar otra vez. La revocación no promete interrumpir un proceso ya iniciado. No almacenar cookies ni extender el consentimiento a nuevas fuentes.
- Cambiar de navegador exige autorización nueva para esa fuente. Inspección/creación explícitas reciben HTTP 403 `browser_consent_required` si el navegador solicitado no coincide con autorización persistida estrictamente verdadera. Cola, retry, worker y comando releen esa configuración: tras revocación confirmada o fuente cambiada usan/registran `none`, no el consentimiento anterior de la tarea.
- Si guardar la revocación falla, la UI bloquea nuevas inspecciones/creaciones con navegador y conserva fallo visible con reintento. El backend sigue la última configuración persistida hasta confirmar el cambio: no prometer revocación de tareas pendientes ni rechazo tras reinicio por una escritura fallida. Antes de crear tarea, volver a comprobar consentimiento tras resolver la validación asíncrona de carpeta.
- Ajustes permanece montado al navegar para conservar un guardado en curso y su resultado/fallo visible al volver, sin persistir resultados de UI en disco.
- Todos los estados, ayuda, botones, presets y acciones están completos en ES/EN; la preferencia de idioma existente se conserva.

## Encontrar y repetir — US-066

El Historial filtra localmente por texto de título, URL o nombre de archivo, sin distinguir mayúsculas/minúsculas, y por estado. Borrar filtros restaura la lista; un resultado vacío distingue historial vacío de búsqueda sin coincidencias. No añade nuevas rutas HTTP, índices ni sincronización.

Antes de encolar se advierte si el enlace exacto, tras quitar espacios exteriores, ya existe en la cola o historial cargados. El usuario puede repetirlo intencionalmente. No se canonizan URLs ni se prohíben duplicados; la advertencia no garantiza detectar equivalencias o tareas no cargadas. La protección existente contra colisión/sobrescritura de archivos permanece obligatoria. La búsqueda no publica enlaces ni modifica registros o archivos.

## Verificación requerida

Pruebas unitarias/React con casos de éxito, pendiente, fallo y valor desconocido; API/IPC con entradas hostiles de estimación; regresión de retry, cookies y colisiones. Las pruebas aisladas no acreditan aceptación Windows. MAN-US-062–MAN-US-066 deben ejecutarse en el paquete real con ES/EN, teclado y configuración declarada antes de `accepted`; codec compatible se comprueba mediante FFprobe y la conservación de archivos mediante hashes. Nombres de pruebas solo se incorporan a fichas cuando existan en el inventario.
