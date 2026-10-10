# Matriz de trazabilidad

Formato: `Historia | contrato | símbolo/componente | prueba actual | evidencia requerida | release | estado`.

| Historia | Contrato | Símbolo/componente | Prueba actual | Evidencia requerida | Release | Estado |
|---|---|---|---|---|---|---|
| US-001 | `POST /directories/validate` | `ensure_output_directory` | `test_ensure_output_directory_creates_missing_directory` | primer arranque | 2.1.0 | partial |
| US-002 | `DirectoryCheck` | `directory_service`/React | directory service + `validates the destination before queueing` | rutas Windows | 2.1.0 | partial |
| US-003 | preflight UI | `NewDownload` | React destination validation | recuperación sin perder inspección | 2.1.0 | partial |
| US-004 | directory validation | FastAPI create/validate | `test_create_download_returns_structured_directory_error` | abuso renderer | 2.1.0 | partial |
| US-010 | `POST /media/inspect` | `inspect_media` | `test_inspect_media_returns_normalized_metadata` | E2E-US-010 | 2.1.0 | partial |
| US-011 | `MediaInspection` | `normalize_info` | `test_normalize_info_exposes_audio_and_video_presets` | E2E-US-011 | 2.1.0 | partial |
| US-012 | normalized formats | `normalize_info`/download options | omit storyboard + reject format | E2E-US-012 | 2.1.0 | partial |
| US-013 | structured session error | error mapper/engine runner | locked browser + DPAPI + consent | E2E-US-013 | 2.1.0 | partial |
| US-020 | `POST/GET /downloads` | queue/store | enqueue + recovery + API collection | E2E-US-020 | 2.1.0 | partial |
| US-021 | progress contract | parser/worker/UI | parser + progress endpoint + active strip | E2E-US-021 | 2.1.0 | partial |
| US-022 | `/cancel` | engine runner/worker | kill timeout + UI cancel | GAP-US-022-API/E2E | 2.1.0 | partial |
| US-023 | `/retry` | downloader/API | retry API + `test_retry_download_reuses_id_without_duplicate_history` | E2E-US-023 | 2.1.0 | partial |
| US-024 | final `filename` | worker/FFmpeg | postprocessed filename + bundled FFmpeg | GAP-US-024-FFPROBE | 2.1.0 | partial |
| US-025 | shutdown limpio | backend/workers/Electron | `test_shutdown_endpoint` + worker shutdown | MAN-US-025 | 2.1.0 | partial |
| US-030 | `GET /downloads` | SQLite store/recovery | roundtrip + idempotent migration + recovery | E2E-US-030 | 2.1.0 | partial |
| US-031 | open by ID | file-actions/preload | safe target + UI identifier | E2E-US-031 | 2.1.0 | partial |
| US-032 | open folder by ID | file-actions/preload | safe target + UI action by ID | E2E-US-032 | 2.1.0 | partial |
| US-033 | `DELETE /downloads/{id}` | store/API | delete API + `test_delete_download_preserves_completed_file` | E2E-US-033 | 2.1.0 | partial |
| US-040 | privacy contract | logging/cookies/token | redaction + consent + token | E2E-US-040 secret scan | 2.1.0 | partial |
| US-041 | enumerated IPC | preload/ipc-contract/window | IPC contract + `electron-security.test.js` | packaged abuse E2E | 2.1.0 | partial |
| US-042 | loopback + token | backend launcher/FastAPI | token protection | GAP-US-042-LISTENER | 2.1.0 | partial |
| US-043 | local diagnostics | logging/diagnostics/UI | data-dir logging + redacted bounded export + UI action | packaged export E2E | 2.1.0 | partial |
| US-050 | standalone installer | PyInstaller/electron-builder/runtime | package build + bundled FFmpeg/Node resolvers + packaged smoke | clean Windows 10/11, physical PC or VM | 2.1.0 | partial |
| US-051 | verified update | engine/app updater | checksum + promotion + active wait | E2E-US-051 | 2.1.0 | partial |
| US-052 | rollback | engine/app updater | reject checksum + retry interval | GAP-US-052-APP | 2.1.0 | partial |
| US-053 | signed NSIS | electron-builder/release | unsigned NSIS build | Authenticode `Valid` + SHA-256 | 2.1.0 | blocked |
| US-054 | preservación al desinstalar | NSIS/installed smoke | sin prueba instalada automatizada | MAN-US-054 | 2.1.0 | blocked |
| US-060 | accesibilidad AA | React/CSS/Electron | flujos React parciales | MAN-US-060 | 2.1.0 | partial |
| US-061 | interfaz ES/EN | i18n/React/config | cambio de idioma y navegación española | MAN-US-061 | 2.1.0 | partial |
| US-062 | estado/borrador de sesión | App/NewDownload/TransferStrip | workflow-ux.test.jsx: lectura, inspección, draft, queueing y prioridad; verde pendiente | MAN-US-062 | Unreleased | partial |
| US-063 | presets y estimated_bytes API/IPC | media_service/directory_service/ipc-contract/NewDownload | workflow-ux.test.jsx: presets y espacio; API/IPC y FFprobe pendientes | MAN-US-063 | Unreleased | partial |
| US-064 | códigos traducidos/rechazo IPC message/detail | i18n/App/DownloadCard/main/preload | workflow-ux + preload-errors: errores, idioma y serialización | MAN-US-064 | Unreleased | partial |
| US-065 | PUT config/HTTP403 consentimiento vigente | App/Settings/NewDownload/config/queue/engine | workflow-ux + API/queue/engine: fuente, revocación y recheck; persistencia real pendiente | MAN-US-065 | Unreleased | partial |
| US-066 | ADR-003/filtro y repetición local | History/NewDownload/downloader | workflow-ux.test.jsx: search/filter/duplicate; verde pendiente | MAN-US-066 | Unreleased | partial |
| BUG-001 | `DirectoryCheck` | directory service/API/React | directory tests + React preflight | Windows clean acceptance | 2.1.0 | fixed |
| QUALITY-001 | ADN/SDD/TDD ejecutable | contract validator + quality gates | validator tests + gate PR | `artifacts/quality/quality-pr.json` | 2.1.0 | fixed |

Una historia solo cambia a `accepted` cuando sus pruebas automatizadas pasan y la evidencia E2E/manual está archivada con fecha, versión y hash.
