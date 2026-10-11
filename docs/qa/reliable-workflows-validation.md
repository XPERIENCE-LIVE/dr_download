# Validación de descargas recuperables

El código del commit `7cb2d9e5f87390a23a7f226732e6cc4daa044947` pasó el gate PR y el smoke real del paquete Windows x64. Este informe documenta esa ejecución, no acepta las historias US-062–US-066 ni certifica una release. Las modificaciones posteriores de documentación no cambian el commit atribuido al paquete.

## Código y gate

- 217 pruebas Python y 93 Jest pasan; validador contractual, integridad Python, lint y build pasan.
- [CI quality-pr](https://github.com/XPERIENCE-LIVE/dr_download/actions/runs/37889788506) pasó también `npm ci` en Windows limpio, con npm 10.9.9 y el lockfile corregido.
- Auditoría npm: cero altas/críticas, 26 moderadas transitivas de herramientas de desarrollo; dependencias declaradas de producción sin hallazgos npm. Esto no sustituye una auditoría de seguridad completa.
- El gate local registra el mismo commit y fingerprint de workspace `822AE21C025B2B4198576850BCF45B087FADDB5CA180BC6549D0AA3BC500233E` en `artifacts/quality/quality-pr.json`.

## Paquete real

Ejecución del 2026-10-09, 05:44:27–05:46:02 UTC, en Windows 10 x64 con Electron 43.7.9. Se usó un perfil nuevo y aislado, sin preparar previamente la caché del motor. Se ejecutó el contenido `win-unpacked` del build; el instalador se identificó y hasheó, pero no se instaló.

- Inicio real, inspección de enlace, navegación ES/EN, guardado de ajustes, selección simple/avanzada y conservación del borrador/formato pasan.
- Una petición con ruta relativa atravesó IPC/contextBridge y devolvió `invalid_path` con recuperación, sin crear tareas ni acceder al enlace.
- Se descargaron tres archivos reales y diferentes; FFprobe comprobó sus streams. Búsqueda, filtro de estado y aviso de repetición operaron sobre ese historial real.
- Se verificaron hashes de los siete artefactos del paquete antes y después de la ejecución, y de los tres archivos después de limpiar exclusivamente los procesos de prueba. Los archivos se conservaron.

| Formato | Bytes | Streams comprobados |
| --- | ---: | --- |
| `audio-mp3` | 7 766 828 | MP3 audio |
| `video-best` | 22 967 690 | AV1 vídeo + AAC audio |
| `video-compatible` | 37 610 585 | H.264 vídeo + AAC audio |

Identidad SHA-256 del instalador de prueba `Dr-Download-Setup-2.1.0-x64.exe`: `A3BEC559348E42DDA48B151411955BEFA17FF652BCF1759100972249388BE762`.

Identidad SHA-256 de `app.asar`: `FAD61CEF08E7F5D3E9B6B09356D4DD2E9B07A3965B93C5669F9F298F6CD58663`.

Evidencia local preservada en `electron/test-artifacts/packaged-smoke-20261008-234416-748/`: `evidence.json`, `source-commit.txt`, `ui-result.json` y capturas ES/EN e historial. Son artefactos de ejecución excluidos de Git; el informe no presume que esos archivos estén disponibles en otro equipo. Los intentos previos bloqueados permanecen separados y no se reutilizan como aprobación.

## Límites pendientes

El instalador está `NotSigned`, `installer_lifecycle_verified` es falso y `public_release_ready` es falso. Faltan instalación/desinstalación en una cuenta o VM Windows aislada, la matriz manual completa, firma SignPath y verificación posterior de Authenticode. La ejecución no acredita consentimiento/revocación manual con sesiones reales de navegadores ni todos los escenarios de fallo. Las historias y el ledger permanecen partial/open según sus matrices; no se publica ni integra directamente en main.
