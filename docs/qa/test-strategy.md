# Estrategia de pruebas

1. TDD: prueba roja, implementación mínima, prueba verde, regresión.
2. Unitarias: servicios de carpeta, estados, errores, checksum y redacción.
3. Integración: FastAPI + SQLite + worker real controlado.
4. Electron: preload, sender, navegación, backend y acciones de archivos.
5. E2E: interfaz compilada, inspección, cola, descarga y archivo reproducible.
6. Manual: Windows 10/11, escalas 100/125/150 %, Edge/Firefox/sin cookies.

Las pruebas unitarias pueden aislar una frontera con un doble controlado, pero no cuentan como evidencia de aceptación. E2E y release ejecutan los binarios, procesos, rutas, SQLite, IPC y archivos reales. No existe modo de omitir gates ni éxito degradado.

## Gates automáticos

Los siguientes nombres y rutas definen **contratos objetivo**. `quality:pr` y `quality:release` existen en el repositorio; su existencia o una ejecución anterior no demuestra cumplimiento de todos los gates normativos. Post-SignPath y el smoke nightly requieren implementación/verificación y evidencia propias. Una discrepancia entre el script actual y el contrato conserva el gate bloqueado, no modifica este requisito ni acredita PASS del commit actual.

- `npm run quality:pr`: contrato SDD, registro anti-duplicación, pytest, Jest, lint y build.
- `npm run quality:release`: gate unsigned previo a SignPath; ejecuta todo el gate PR, PyInstaller/NSIS, aplicación empaquetada, descarga real de audio y vídeo, FFprobe y SHA-256 unsigned, y registra `publishable: false`.
- `npm run quality:post-sign`: gate posterior a recibir el artefacto firmado de SignPath; valida SHA-256 signed, Authenticode `Valid`, timestamp, publisher `SignPath Foundation`, instalación, inicio y desinstalación del instalador exacto.
- `.github/workflows/nightly-real.yml`: ejecuta el smoke externo programado sin sustituir el gate PR determinista.

No existen switches de omisión. Cada ejecución escribe evidencia JSON en `artifacts/quality`; un archivo de evidencia de otro commit o configuración no es reutilizable.

## Contrato de identidad y evidencia

- `QA-GATE-PR-001`: las pruebas, lint, build y validador contractual deben aprobar el mismo SHA protegido por Pull Request.
- `QA-GATE-EVIDENCE-001`: cada evidencia registra versión, commit, sistema, arquitectura, configuración, fecha, comando, código de salida, artifact-id y hashes aplicables.
- `QA-GATE-ARTIFACT-001`: los gates unsigned y post-SignPath reciben una ruta e identidad explícitas; no seleccionan “el más reciente” y no recompilan entre prueba, firma y publicación.
- `QA-GATE-RELEASE-UNSIGNED-001`: el gate previo a firma termina con el hash unsigned y `publishable: false`; la validación de Authenticode pertenece exclusivamente al gate post-SignPath.
- Unitarias e integración pueden aislar fronteras, pero solo E2E/acceptance/release con procesos reales acreditan su nivel.
- El release prueba el NSIS exacto: instalación, inicio, SQLite, IPC, yt-dlp, FFmpeg/FFprobe, duración y tipo de streams, procesos, preservación de datos y desinstalación.
- Windows 10/11 y cada combinación manual declaran ejecutor, fecha, configuración, estado y ruta de evidencia.
- Una historia solo cambia a `accepted` cuando su evidencia coincide con el SHA, versión, matriz y artefacto declarados.
- Una falla conserva la salida original, abre o reabre su ID y vuelve a prueba roja, corrección mínima y regresión; nunca reduce aserciones ni produce éxito degradado.

La evidencia documental no resuelve los hallazgos de `docs/qa/audits/2026-07-19-hierarchical-qa-audit.md`. Solo una ejecución fresca puede satisfacer el gate correspondiente.

## Cobertura de experiencia confiable

US-062–US-066: `electron/src/__tests__/workflow-ux.test.jsx` comprueba lecturas, inspección indeterminada, prioridad del pie, navegación, encolado, presets, espacio, errores, filtros, repetición y guardado con fronteras aisladas. Backend/IPC comprueban estimaciones estrictas, codecs compatibles y rechazo de selectores no permitidos. Las fichas declaran nombres existentes y los casos pendientes, sin convertir mocks en aceptación.

Completar MAN-US-062–MAN-US-066 en binarios reales ES/EN y teclado, incluyendo backend detenido, escritura fallida/revocación tras reinicio, FFprobe H.264/AAC MP4, búsqueda por cada campo y hashes de archivos preservados al repetir. El mismo universo debe estar en épicas, fichas y ambas matrices; los casos manuales siguen pending hasta una ejecución verificable.

Consentimiento: API inspect/create HTTP403 para autorización ausente/falsa/fuente distinta; recheck vigente de cola/retry/worker/comando y none registrado tras revocación confirmada; UI reevalúa tras validación de carpeta. Probar fallo de revocación como bloqueo local con reintento, sin inventar persistencia. IPC: `preserves structured backend failures across the serialized IPC boundary` comprueba rechazo simple message/detail; falta prueba real contextBridge en paquete para aceptación completa. Ajustes conserva guardado y resultado al navegar.
