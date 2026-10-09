# Publicación Windows

## Estado de implementación

Esta guía define **contratos objetivo**. El repositorio ya contiene build y gates PR/release, pero su existencia no certifica instalación limpia, aprobación de historias ni separación unsigned/post-SignPath conforme al ADN. Validar el comportamiento y la evidencia del script actual frente a este contrato; cualquier gap conserva la release bloqueada. Ningún PASS de otro SHA o observado solo en un workspace se atribuye al candidato actual.

## Contrato objetivo de build interno

```powershell
python -m pip install -r backend/requirements-build.txt
npm ci --prefix electron
npm run package:win --prefix electron
```

El pipeline compila React, empaqueta FastAPI con PyInstaller y crea un NSIS x64 por usuario. La desinstalación conserva preferencias e historial.

## Puertas de publicación

- `QA-GATE-RELEASE-UNSIGNED-001`: GitHub Actions construye un único NSIS x64 y registra artifact-id, commit y SHA-256 unsigned. El contrato objetivo `tools/quality-gate.ps1 -Level release` debe probar ese artefacto, finalizar con código 0 y registrar `publishable: false`.
- `QA-GATE-SIGN-001`: el mismo artifact-id se envía a SignPath con aprobación humana. Solo después de recibir el artefacto firmado, el gate post-SignPath objetivo valida SHA-256 signed, Authenticode `Valid`, timestamp válido y publisher `SignPath Foundation`.
- FFmpeg/FFprobe x64 incluidos, sus hashes archivados y licencias reflejadas en `THIRD_PARTY_NOTICES.md`.
- Repositorio de GitHub Releases configurado mediante `DR_DOWNLOAD_UPDATE_OWNER` y `DR_DOWNLOAD_UPDATE_REPO`.
- Instalación, actualización, roll-forward y desinstalación del NSIS exacto probadas en Windows 10/11 limpios.
- Descarga real autorizada de audio y video; archivos reproducibles y logs sin secretos.
- Todas las historias del alcance vigente, derivadas de las fichas y coincidentes con ambas matrices, deben estar `accepted` con evidencia real; alternativamente, producto debe aprobar una reducción de scope.

Nunca se publica un instalador sin firmar. Un build interno o una ejecución sin SignPath completa debe registrar `publishable: false`.

El workflow `quality-release` solo construye y conserva un artefacto verificable; no publica una Release automáticamente. `QA-GATE-PUBLISH-001` exige una acción posterior del `release approver` que publique únicamente el SHA-256 firmado validado, sin recompilar ni reemplazar assets bajo el mismo tag.

## Evidencia por etapa

| Etapa | Responsable | Evidencia | Bloqueo |
| --- | --- | --- | --- |
| Build único | `author` | commit, tag, run, artifact-id y SHA-256 unsigned | Identidad ausente o más de un build candidato |
| Gate unsigned previo a firma | `reviewer` | instalación, inicio, streams, procesos, datos, desinstalación, SHA-256 unsigned y `publishable: false` | Se prueba `win-unpacked`, otro archivo, falta un resultado o se intenta verificar firma |
| Firma SignPath | `release approver` | solicitud, aprobación y artifact-id | SignPath no devuelve el artefacto firmado o cambia su origen |
| Gate post-SignPath | `reviewer` | SHA-256 signed, instalación, inicio, desinstalación, publisher, timestamp y Authenticode `Valid` | Firma no `Valid`, configuración ausente, publisher distinto o prueba incompleta |
| Publicación | `release approver` | aprobación final, tag y hash del asset | Hash distinto, evidencia incompleta o gate abierto |

Cada etapa consume la identidad emitida por la anterior. Una discrepancia invalida el candidato completo.

## Recuperación

La aplicación no se reinicia con descargas activas. Si una actualización falla, el reemplazo no se promueve y permanece la última versión previamente verificada. Si no existe una versión verificada de yt-dlp, la descarga queda bloqueada con error accionable.

Un defecto de aplicación ya publicado activa `QA-GATE-ROLLFORWARD-001` y `docs/operations/rollback-runbook.md`: se congela el canal, se parte del último tag bueno, se crea un parche superior y se repite el pipeline completo con un artefacto nuevo y firmado antes de reabrir el canal.

## Gate específico de carpetas

Antes de publicar, probar una carpeta nueva, una ruta relativa, un archivo usado como carpeta, una carpeta sin permisos y un volumen con poco espacio. La UI debe mostrar `error_code`, causa y recuperación; nunca publicar el error técnico sin traducir.

La ampliación aprobada US-062–US-066 añade espacio estimado estricto API/IPC, compatible MP4 H.264/AAC sin sustitución, conectividad y operaciones veraces, borrador de sesión, guardado/consentimiento, recuperación ES/EN y búsqueda/filtro/repetición protegida. Sus nuevos MAN-US-062–MAN-US-066 permanecen pending; no se excluyen del universo de release ni se aceptan por documentación o Jest aislado.
