# Changelog

## Unreleased — experiencia confiable

- US-062–US-066 documentan conexión confirmada, inspección indeterminada, encolado diferenciado, borrador de sesión y acceso explícito a Cola.
- Presets simples de vídeo compatible H.264/AAC MP4, mejor vídeo y MP3; audio original/streams avanzados y tamaño desconocido explícito.
- `estimated_bytes` opcional estricto en API/IPC eleva preflight a max(128 MiB, dos veces la estimación), sin debilitar permisos ni protección de archivos.
- Recuperación ES/EN por código, guardado confirmado y consentimiento revocable; fallo de consentimiento bloquea nuevas operaciones con cookies.
- ADR-003 aprueba búsqueda/filtro local de historial y aviso no prohibitivo de enlaces repetidos. Pegado múltiple, reordenar y pausar/reanudar quedan en backlog.
- El motor revalida el consentimiento persistido del navegador en cola, reintentos y comandos; los errores estructurados conservan su detalle al atravesar Electron IPC y contextBridge.
- Smoke de tres formatos con identidad explícita del paquete, H.264/AAC comprobado por FFprobe y hashes de archivos preservados; no acredita instalación/desinstalación ni firma.
- Dependencias compatibles actualizadas y herramientas Jest/Babel-Jest/jsdom 30.5.2 para eliminar vulnerabilidades altas del gate. La auditoría conserva 26 moderadas transitivas de desarrollo; producción sin hallazgos npm.
- Fichas, matrices, CLAUDE.md, ADN y guardrails enlazan el contrato; nuevas historias permanecen partial y su aceptación Windows pendiente. Los conteos y smokes registrados abajo son históricos, no evidencia del commit actual.

## Unreleased — Quality Gates ejecutables

- Se añadió un gate SDD que valida historias, épicas, matrices, evidencia `accepted`, ADN y ledger anti-duplicación.
- Los gates PR/release comparten un único script PowerShell bloqueante en Windows con evidencia JSON.
- El smoke empaquetado descarga audio y vídeo reales y valida sus streams con FFprobe.
- El runtime falla de forma explícita si falta yt-dlp.exe, Node, backend o renderer compilado; se eliminó el motor Python alternativo.
- GitHub Actions usa Python 3.13 y Node 22; el release requiere ambiente protegido y Authenticode válido.
- El gate PR comprueba además integridad del entorno Python y auditoría npm bloqueante desde severidad alta.
- La configuración JSON y el historial SQLite fallan de forma cerrada: un archivo corrupto nunca se reemplaza ni se oculta con valores vacíos.
- Evidencia local actual: 96 pruebas Python y 31 Jest; el smoke empaquetado descargó y validó con FFprobe audio MP3 y vídeo MP4 reales.
- El gate de release se bloquea deliberadamente mientras el instalador permanezca sin firma Authenticode.

## Unreleased — documentación SDD+TDD

- Se expandieron US-010–US-053 en 21 fichas completas con criterios Given/When/Then, pruebas, evidencia y riesgos.
- Se individualizaron las matrices de aceptación y trazabilidad.
- Se registraron gaps de cobertura con IDs estables para evitar evidencia implícita o inventada.

## Unreleased — robustez de producción

- Node.js se incluye y se pasa explícitamente a yt-dlp; ya no depende del runtime del equipo.
- Reintentos idempotentes conservan el ID y el borrado de historial preserva archivos.
- La cancelación termina el árbol de procesos en Windows sin shell.
- Electron valida sender/main frame y prueba aislamiento y bloqueo de navegación.
- Logs rotativos se guardan en `userData`; la UI exporta diagnósticos locales redactados y acotados.

## 2.1.0

- New Studio Professional interface in Spanish and English.
- Media inspection, queue, automatic progress, history, cancel and retry.
- SQLite persistence with idempotent JSON migration.
- Edge, Firefox and cookie-free modes with explicit consent.
- Secure Electron IPC, dynamic backend port and session token.
- Verified yt-dlp executable updates with atomic rollback.
- Windows NSIS/PyInstaller packaging, branded icon and update-ready release channel.
# Unreleased

- Corregida la carpeta de salida: se crea y valida automáticamente, con errores estructurados y recuperación desde la interfaz.
- Añadido `POST /directories/validate` y validación IPC enumerada.
- Corregido el registro del archivo final después de la conversión FFmpeg.
