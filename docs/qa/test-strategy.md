# Estrategia de pruebas

1. TDD: prueba roja, implementación mínima, prueba verde, regresión.
2. Unitarias: servicios de carpeta, estados, errores, checksum y redacción.
3. Integración: FastAPI + SQLite + worker real controlado.
4. Electron: preload, sender, navegación, backend y acciones de archivos.
5. E2E: interfaz compilada, inspección, cola, descarga y archivo reproducible.
6. Manual: Windows 10/11, escalas 100/125/150 %, Edge/Firefox/sin cookies.

Las pruebas unitarias pueden aislar una frontera con un doble controlado, pero no cuentan como evidencia de aceptación. E2E y release ejecutan los binarios, procesos, rutas, SQLite, IPC y archivos reales. No existe modo de omitir gates ni éxito degradado.

## Gates automáticos

- `npm run quality:pr`: contrato SDD, registro anti-duplicación, pytest, Jest, lint y build.
- `npm run quality:release`: todo el gate PR, PyInstaller/NSIS, aplicación empaquetada, descarga real de audio y vídeo, FFprobe, SHA-256 y Authenticode.
- `.github/workflows/nightly-real.yml`: ejecuta el smoke externo programado sin sustituir el gate PR determinista.

No existen switches de omisión. Cada ejecución escribe evidencia JSON en `artifacts/quality`; un archivo de evidencia de otro commit o configuración no es reutilizable.

## Contrato de identidad y evidencia

- `QA-GATE-PR-001`: las pruebas, lint, build y validador contractual deben aprobar el mismo SHA protegido por Pull Request.
- `QA-GATE-EVIDENCE-001`: cada evidencia registra versión, commit, sistema, arquitectura, configuración, fecha, comando, código de salida, artifact-id y hashes aplicables.
- `QA-GATE-ARTIFACT-001`: el gate release recibe una ruta e identidad explícitas; no selecciona “el más reciente” y no recompila entre prueba, firma y publicación.
- Unitarias e integración pueden aislar fronteras, pero solo E2E/acceptance/release con procesos reales acreditan su nivel.
- El release prueba el NSIS exacto: instalación, inicio, SQLite, IPC, yt-dlp, FFmpeg/FFprobe, duración y tipo de streams, procesos, preservación de datos y desinstalación.
- Windows 10/11 y cada combinación manual declaran ejecutor, fecha, configuración, estado y ruta de evidencia.
- Una historia solo cambia a `accepted` cuando su evidencia coincide con el SHA, versión, matriz y artefacto declarados.
- Una falla conserva la salida original, abre o reabre su ID y vuelve a prueba roja, corrección mínima y regresión; nunca reduce aserciones ni produce éxito degradado.

La evidencia documental no resuelve los hallazgos de `docs/qa/audits/2026-07-19-hierarchical-qa-audit.md`. Solo una ejecución fresca puede satisfacer el gate correspondiente.
