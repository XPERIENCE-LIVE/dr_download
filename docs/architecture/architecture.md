# Arquitectura

La validación de destino vive en `backend/directory_service.py` y se expone por `POST /directories/validate`. Tanto esa ruta como `POST /downloads` crean la carpeta predeterminada, realizan una escritura temporal y verifican el espacio mínimo antes de permitir la cola. React solo recibe el resultado estructurado mediante el contrato IPC enumerado.

La estimación opcional no negativa validada por API/IPC eleva el mínimo de creación de tarea a `max(128 MiB, 2 * estimated_bytes)`; React también compara ese umbral con el espacio libre devuelto por validación de carpeta. No cambia la política de ruta, escritura ni colisiones. El [contrato de experiencia](../product/experience-reliability.md) mantiene borrador y búsqueda/filtro en React, confirmación/errores en las operaciones existentes y presets/validación en backend; no añade servicio, dependencia ni endpoint para historial.

```text
React renderer (sandbox)
        │ operaciones enumeradas
        ▼
Electron preload / main ── select folder, open path, notifications
        │ HTTP 127.0.0.1 + token aleatorio + puerto dinámico
        ▼
FastAPI ── cola ── yt-dlp.exe actualizable obligatorio
   └── SQLite + preferencias locales
```

## Seguridad

El renderer no recibe `ipcRenderer`, filesystem ni una función HTTP genérica. `ipc-contract.js` transforma únicamente operaciones conocidas. Electron valida el `webContents` emisor; el backend exige `X-Dr-Download-Token` cuando lo inicia la aplicación. CSP bloquea conexiones del renderer, ventanas nuevas y navegación.

Consentimiento se comprueba en backend por fuente y booleano persistido estrictamente verdadero al inspeccionar/crear y antes de lectura en cola/retry/worker/comando. Main/preload transportan fallos como envoltura/rechazo simple message/detail que sobrevive IPC/contextBridge; React traduce el código sin asumir una instancia Error. [API](api-contract.md) e [IPC](ipc-contract.md) detallan rechazos, revocación y límites.

## API

- `POST /media/inspect`
- `POST /downloads`
- `GET /downloads` y `/downloads/{id}`
- `POST /downloads/{id}/cancel` y `/retry`
- `DELETE /downloads/{id}`
- `GET /config/` y `PUT /config`
- Adaptadores temporales: `/download/`, `/progress/{id}`, `/history/` y `POST /config/`.

Estados: `queued`, `inspecting`, `downloading`, `postprocessing`, `completed`, `failed`, `cancelled`.

## Persistencia y actualización

SQLite guarda el payload de cada tarea; el JSON histórico se importa una sola vez y se respalda como `.bak`. El actualizador del motor comprueba como máximo cada 24 horas, verifica `SHA2-256SUMS`, ejecuta `--version`, conserva `.previous` y reemplaza atómicamente.

El runtime es fail-closed: durante el primer arranque el backend no publica salud ni acepta trabajo hasta tener un yt-dlp.exe descargado, verificado por SHA-256 y aprobado por `--version`. Si falta yt-dlp.exe, Node, backend empaquetado o el HTML compilado canónico, la aplicación muestra un error y detiene la operación. No cambia a otro motor, runtime o layout.
