# Mecanismos antifallos

## Principios

- Fallar cerrado: nunca encolar ni escribir si el destino, token o contrato no son válidos.
- Degradación segura: un fallo de actualización conserva la versión anterior funcional.
- Idempotencia: validar directorios, migrar historial y reintentar no duplican datos.
- Transparencia: todo error visible contiene causa, recurso afectado y acción sugerida.

## Tabla de fallos

| Fallo | Detección | Respuesta segura | Recuperación |
|---|---|---|---|
| Carpeta inválida | `DirectoryCheck` negativo | bloquear cola | usar Descargas o elegir otra |
| Backend detenido | timeout/connection refused | marcar motor no disponible | reiniciar backend y reintentar |
| Primer arranque lento | salud autenticada pendiente mientras el proceso sigue vivo | esperar hasta 120 s transcurridos, con timeout de 2 s por petición; rechazar antes si el proceso termina | comprobar red inicial y reintentar; exportar diagnóstico si persiste |
| yt-dlp/FFmpeg termina | exit code y estado | `failed`, conservar diagnóstico redactado | reintentar sin duplicar |
| Cancelación | señal y `wait()` | matar árbol de procesos, limpiar temporal | estado `cancelled` |
| SQLite corrupto | error de apertura | fallar cerrado, conservar archivo original sin reemplazarlo por historial vacío | exportar diagnóstico y restaurar un backup válido con revisión |
| Checksum incorrecto | hash no coincide | no reemplazar binario | conservar versión anterior |
| Disco lleno | espacio mínimo/estimado o fallo durante descarga | bloquear cola o marcar failed; no simular pausa/reanudación | liberar espacio o elegir carpeta y reintentar |
| Actualización incompleta | health check fallido | rollback atómico | continuar con versión instalada |
| URL de stream caducada (ADR-004) | TTL de sesión o 403 del proveedor | 410 `stream_expired`; no reintentar en bucle | **Volver a cargar** resuelve de nuevo |
| Proveedor rechaza el stream | exit code de FFmpeg o 403 | terminar proceso, `stream_unavailable` con diagnóstico redactado | actualizar motor y reintentar |
| Cliente desconecta o busca | cierre del `StreamingResponse` o nueva petición | matar árbol de FFmpeg de esa sesión | ninguno; proceso con dueño |
| SponsorBlock caído | timeout de 5 s o error HTTP | seguir sin saltos, `sponsorblock_unavailable` visible | reintentar en el siguiente vídeo |
| Lista demasiado grande | más de 500 entradas | no crear nada, `playlist_too_large` con el número encontrado | importar una lista más pequeña |

## Invariantes verificables

1. No hay descarga sin carpeta aceptada.
2. No se registran cookies ni credenciales.
3. Cada proceso hijo tiene dueño y limpieza comprobable.
4. Cada archivo `completed` existe y es el producido por el motor.
5. Toda migración y reintento es idempotente.

6. Inspección indeterminada, disponibilidad confirmada por lecturas y guardado pendiente/fallido nunca muestran éxito ni cifras inventadas.
7. Consentimiento no persistido no habilita cookies; revocación confirmada impide nuevas operaciones autorizadas por ese consentimiento.

   Backend verifica autorización estricta por fuente en API/cola/retry/worker/comando. Revocación fallida conserva bloqueo UI para nuevas inspecciones/creaciones y un error de guardado visible; la configuración backend anterior permanece hasta guardado confirmado. No prometer interrupción de procesos ya iniciados ni persistencia de una escritura fallida.
8. La advertencia de repetición permite continuar y no elimina protección contra colisiones; filtrado local no modifica registros ni archivos.
9. Reproducción (ADR-004): como máximo un proceso FFmpeg por sesión; cerrar la aplicación no deja procesos de reproducción; URLs de stream, cabeceras y token nunca llegan al renderer ni a los registros.

Los errores y acciones se traducen por código conforme a [copy ES/EN](../design/error-copy.md); [experiencia confiable](../product/experience-reliability.md) define conservación de enlace, borrador, ID y datos durante recuperación.

El helper existente `waitForBackend`, compartido desde `backend-client.js`, mantiene `/health` autenticado y la verificación fail-closed del motor antes de declarar servicio disponible. En un perfil nuevo, el primer arranque observado tardó 26,68 s (aproximadamente 27 s): es un diagnóstico que explica por qué el límite previo de 15 s impedía cargar el renderer, no evidencia de aceptación ni garantía de latencia. Sin motor previamente verificado en caché, el primer arranque todavía necesita red para obtenerlo y verificarlo; el límite de 120 s no habilita un motor alternativo ni convierte fallo en éxito.

Regresión aislada: `backend-startup.test.js` contiene `waits for a healthy first startup that takes longer than fifteen seconds`, `stops waiting as soon as the backend process exits` y `rejects an unready backend after the bounded startup deadline`. El smoke del runtime empaquetado debe complementar estos tests; [el informe de validación](../qa/reliable-workflows-validation.md) conserva su alcance, identidad y límites.
