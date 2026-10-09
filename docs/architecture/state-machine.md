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

El worker/retry/cola/comando comprueba consentimiento estricto y fuente persistida vigente, sin reutilizar autorización histórica; tras revocación confirmada o cambio de fuente usa y registra none. Fallar al guardar revocación bloquea inspect/create del navegador en la UI, pero no cambia el estado persistido backend ni garantiza rechazo tras reinicio. Ajustes permanece montado durante navegación y conserva resultado/fallo pendiente; la creación reevalúa consentimiento después de validar carpeta asíncronamente.
