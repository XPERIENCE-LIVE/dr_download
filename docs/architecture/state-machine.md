# Máquina de estados

```text
queued -> inspecting -> downloading -> postprocessing -> completed
   |          |              |              |
   +----------+--------------+--------------+--> failed
   +--------------------------------------------> cancelled
```

`completed` solo se emite cuando el archivo final existe y tiene tamaño mayor que cero. `postprocessing` cubre FFmpeg y la normalización del nombre final.

La inspección previa de Nueva descarga y el encolado pendiente son estados de operación UI, no porcentajes ni nuevas tareas persistidas. La inspección presenta actividad indeterminada. La disponibilidad backend se deriva de lecturas: comprobando antes de resolver, disponible tras éxito, desconectado tras fallo. El pie prioriza `inspecting/downloading/postprocessing` sobre `queued` y traduce sus fases.

Guardar ajustes/consentimiento tiene pendiente, confirmado y fallido; un rechazo conserva fallo visible y no autoriza cookies. Revocar confirmado bloquea nuevas operaciones con cookies. El borrador dura la sesión; las tareas e historial conservan la persistencia existente. No se añaden estados `paused/resumed`: son [backlog diferido](../product/backlog.md).

## Sesión de reproducción (planificada, ADR-004)

```text
resolving -> buffering <-> playing <-> paused -> ended
    |            |            |                    
    +------------+------------+--> failed (código + recuperación)
seeking: playing/paused -> buffering (nuevo proceso en start)
expired: TTL 4 h -> 410 stream_expired -> resolving (acción explícita)
```

`resolving` es indeterminado, sin porcentaje. Una sesión de reproducción no es una tarea de descarga ni se guarda en el historial; vive en memoria. En una lista, `ended` o un `failed` de resolución avanzan al siguiente ítem con aviso visible; el último `ended` detiene la lista.

El worker/retry/cola/comando comprueba consentimiento estricto y fuente persistida vigente, sin reutilizar autorización histórica; tras revocación confirmada o cambio de fuente usa y registra none. Fallar al guardar revocación bloquea inspect/create del navegador en la UI, pero no cambia el estado persistido backend ni garantiza rechazo tras reinicio. Ajustes permanece montado durante navegación y conserva resultado/fallo pendiente; la creación reevalúa consentimiento después de validar carpeta asíncronamente.
