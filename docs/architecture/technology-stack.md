# Stack tecnológico y política de coste

## Stack implementado

| Capa | Tecnología | Licencia/uso |
|---|---|---|
| Shell de escritorio | Electron 43 | MIT; runtime Chromium/Node incluido |
| UI | React 18, Vite 6, CSS | MIT/open source |
| Backend local | Python 3.13, FastAPI, Uvicorn, Pydantic | MIT/BSD; empaquetado con PyInstaller |
| Persistencia | SQLite mediante biblioteca estándar Python | dominio público/open source |
| Motor | yt-dlp | revisar obligaciones GPL-3.0 en distribución |
| Runtime JavaScript | Node.js 22.14.0 incluido | MIT y avisos de terceros; no depende del Node del equipo |
| Conversión | FFmpeg/FFprobe | LGPL/GPL según binarios y configuración; avisos incluidos |
| Pruebas | pytest, pytest-asyncio, Jest, Testing Library | open source |
| Empaquetado | electron-builder, NSIS, PyInstaller | open source |
| Actualizaciones | GitHub Releases o servidor estático compatible | sin servicio propietario obligatorio |

## Perfil 100% open source y coste cero

- No se requieren APIs de pago, cuentas, nube, telemetría ni servicios propietarios.
- El desarrollo y CI pueden ejecutarse con herramientas gratuitas/open source.
- GitHub Free es una opción de distribución, no una dependencia de runtime.
- Todos los binarios redistribuidos deben conservar licencias, avisos y hashes.
- Las licencias GPL/LGPL de yt-dlp/FFmpeg deben revisarse antes de publicar.

## Límites honestos del coste cero

La firma Authenticode pública normalmente requiere un certificado de pago o uno aportado por un tercero. Sin certificado, el proyecto sigue siendo open source y distribuible como build interna/no firmada, pero no cumple el criterio de publicación comercial firmada. No se debe simular una firma.

El runtime JavaScript exigido por yt-dlp se copia durante `prepare:runtime` y se resuelve desde `resources/node/node.exe`. La aceptación final aún requiere una VM sin Node instalado.
