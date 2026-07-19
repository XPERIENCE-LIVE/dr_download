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
| yt-dlp/FFmpeg termina | exit code y estado | `failed`, conservar diagnóstico redactado | reintentar sin duplicar |
| Cancelación | señal y `wait()` | matar árbol de procesos, limpiar temporal | estado `cancelled` |
| SQLite corrupto | error de apertura | copia de respaldo y modo solo lectura | restaurar backup |
| Checksum incorrecto | hash no coincide | no reemplazar binario | conservar versión anterior |
| Disco lleno | espacio mínimo/preflight | bloquear o pausar | liberar espacio y reintentar |
| Actualización incompleta | health check fallido | rollback atómico | continuar con versión instalada |

## Invariantes verificables

1. No hay descarga sin carpeta aceptada.
2. No se registran cookies ni credenciales.
3. Cada proceso hijo tiene dueño y limpieza comprobable.
4. Cada archivo `completed` existe y es el producido por el motor.
5. Toda migración y reintento es idempotente.
