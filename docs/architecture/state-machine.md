# Máquina de estados

```text
queued -> inspecting -> downloading -> postprocessing -> completed
   |          |              |              |
   +----------+--------------+--------------+--> failed
   +--------------------------------------------> cancelled
```

`completed` solo se emite cuando el archivo final existe y tiene tamaño mayor que cero. `postprocessing` cubre FFmpeg y la normalización del nombre final.

La inspección previa de Nueva descarga y el encolado pendiente son estados de operación UI, no porcentajes ni nuevas tareas persistidas. La inspección presenta actividad indeterminada. La disponibilidad backend se deriva de lecturas: comprobando antes de resolver, disponible tras éxito, desconectado tras fallo. El pie prioriza `inspecting/downloading/postprocessing` sobre `queued` y traduce sus fases.

Guardar ajustes/consentimiento tiene pendiente, confirmado y fallido; un rechazo conserva fallo visible y no autoriza cookies. Revocar confirmado bloquea nuevas operaciones con cookies. El borrador dura la sesión; las tareas e historial conservan la persistencia existente. No se añaden estados `paused/resumed` a las descargas: son [backlog diferido](../product/backlog.md).

## Sesión de reproducción (implementada; aceptación pendiente, ADR-004)

```text
resolving -> buffering <-> playing <-> paused -> ended
    |            |            |                    
    +------------+------------+--> failed (código + recuperación)
seeking: playing/paused -> buffering (nuevo proceso en start)
expired: TTL 4 h -> 410 stream_expired -> resolving (acción explícita)
```

`resolving` es indeterminado, sin porcentaje. Una sesión de reproducción no es una tarea de descarga ni se guarda en el historial; vive en memoria. La UI usa `playbackError` para el error visible, conserva la causa segura y ofrece Volver a cargar. En una lista, `ended` avanza al siguiente ítem; fallar al resolver lo omite con nombre y causa. El último `ended` detiene la lista y todos los ítems fallidos dejan error. Cerrar o cambiar detiene la sesión; una resolución tardía se descarta y su sesión se termina.

Un fallo del medio antes del primer estado `playing`, en el inicio sin búsqueda, se trata como ítem no disponible: libera su sesión y continúa en la dirección solicitada con un aviso de causa. Si ya reprodujo contenido o falló una búsqueda, conserva el error y detiene; no lo declara fin natural ni oculta contenido perdido.

Buscar mientras está en pausa vuelve a `paused` tras cargar, sin reanudar automáticamente. En un stream nuevo, la UI confirma `actual_start` y espera `canplay` para decodificar el tramo inicial a 4×, oculto y silenciado, reduciendo a 1× durante el último medio segundo para evitar sobrepasar el destino. Solo un fotograma decodificado confirmado por `requestVideoFrameCallback` permite volver a 1× y mostrar/reanudar; si estaba en pausa, vuelve a pausar. No acredita los tiempos de aceptación sin ejecución real.

El worker/retry/cola/comando comprueba consentimiento estricto y fuente persistida vigente, sin reutilizar autorización histórica; tras revocación confirmada o cambio de fuente usa y registra none. Fallar al guardar revocación bloquea inspect/create del navegador en la UI, pero no cambia el estado persistido backend ni garantiza rechazo tras reinicio. Ajustes permanece montado durante navegación y conserva resultado/fallo pendiente; la creación reevalúa consentimiento después de validar carpeta asíncronamente.

La revisión de búsqueda aumenta por intención, incluso si Chromium reintenta una petición anterior. El backend rechaza revisiones atrasadas antes de cancelar procesos; la UI descarta eventos de elementos sustituidos. Solo un EOF al alcanzar la duración conocida y con backend `ended` permite avanzar: un corte temprano muestra error. Para la comprobación del elemento, se admite hasta un segundo de diferencia si los metadatos del proveedor expresan una duración entera redondeada; para duración fraccionaria, 0,25 s. La confirmación del backend y su tratamiento de errores de transporte siguen siendo obligatorios.
