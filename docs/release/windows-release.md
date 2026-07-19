# Publicación Windows

## Build interno

```powershell
python -m pip install -r backend/requirements-build.txt
npm ci --prefix electron
npm run package:win --prefix electron
```

El pipeline compila React, empaqueta FastAPI con PyInstaller y crea un NSIS x64 por usuario. La desinstalación conserva preferencias e historial.

## Puertas de publicación

- `QA-GATE-ARTIFACT-001`: GitHub Actions construye un único NSIS x64 y registra artifact-id, commit y SHA-256 unsigned. `tools/quality-gate.ps1 -Level release` debe finalizar con código 0 sobre ese artefacto y commit.
- `QA-GATE-SIGN-001`: el mismo artifact-id se envía a SignPath con aprobación humana; el resultado debe mostrar Authenticode `Valid`, timestamp válido y publisher `SignPath Foundation`.
- FFmpeg/FFprobe x64 incluidos, sus hashes archivados y licencias reflejadas en `THIRD_PARTY_NOTICES.md`.
- Repositorio de GitHub Releases configurado mediante `DR_DOWNLOAD_UPDATE_OWNER` y `DR_DOWNLOAD_UPDATE_REPO`.
- Instalación, actualización, roll-forward y desinstalación del NSIS exacto probadas en Windows 10/11 limpios.
- Descarga real autorizada de audio y video; archivos reproducibles y logs sin secretos.
- Las 25 historias deben estar `accepted` con evidencia real o una reducción de scope debe estar aprobada por producto.

Nunca se publica un instalador sin firmar. Un build interno o una ejecución sin SignPath completa debe registrar `publishable: false`.

El workflow `quality-release` solo construye y conserva un artefacto verificable; no publica una Release automáticamente. `QA-GATE-PUBLISH-001` exige una acción posterior del `release approver` que publique únicamente el SHA-256 firmado validado, sin recompilar ni reemplazar assets bajo el mismo tag.

## Evidencia por etapa

| Etapa | Responsable | Evidencia | Bloqueo |
| --- | --- | --- | --- |
| Build único | `author` | commit, tag, run, artifact-id y SHA-256 unsigned | Identidad ausente o más de un build candidato |
| Pruebas del NSIS | `reviewer` | instalación, inicio, streams, procesos, datos y desinstalación | Se prueba `win-unpacked`, otro archivo o falta un resultado |
| Firma SignPath | `release approver` | solicitud, aprobación, publisher, timestamp y SHA-256 signed | Firma no `Valid`, configuración ausente o publisher distinto |
| Publicación | `release approver` | aprobación final, tag y hash del asset | Hash distinto, evidencia incompleta o gate abierto |

Cada etapa consume la identidad emitida por la anterior. Una discrepancia invalida el candidato completo.

## Recuperación

La aplicación no se reinicia con descargas activas. Si una actualización falla, el reemplazo no se promueve y permanece la última versión previamente verificada. Si no existe una versión verificada de yt-dlp, la descarga queda bloqueada con error accionable.

Un defecto de aplicación ya publicado activa `QA-GATE-ROLLFORWARD-001` y `docs/operations/rollback-runbook.md`: se congela el canal, se parte del último tag bueno, se crea un parche superior y se repite el pipeline completo con un artefacto nuevo y firmado antes de reabrir el canal.
# Gate específico de carpetas

Antes de publicar, probar una carpeta nueva, una ruta relativa, un archivo usado como carpeta, una carpeta sin permisos y un volumen con poco espacio. La UI debe mostrar `error_code`, causa y recuperación; nunca publicar el error técnico sin traducir.
