# Contrato API local

Todas las rutas requieren `X-Dr-Download-Token` y escuchan solo en `127.0.0.1`.

## `POST /directories/validate`

Entrada: `{ "path": string | null }`.

Salida:

```json
{"accepted":true,"path":"C:\\Users\\...\\Downloads\\Dr. Download","created":true,"writable":true,"free_bytes":0,"error_code":null,"recovery":""}
```

Errores: `invalid_path`, `access_denied`, `disk_full`. La respuesta nunca incluye tokens, cookies ni URL completa.

## Descargas

`POST /downloads` recibe `url`, `format_id`, `output_dir`, `cookie_source`; ejecuta el mismo preflight antes de encolar. Los estados son `queued`, `inspecting`, `downloading`, `postprocessing`, `completed`, `failed`, `cancelled`.

Las rutas antiguas se mantienen como adaptadores durante una versión.
