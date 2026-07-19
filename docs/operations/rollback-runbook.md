# Runbook de recuperación por roll-forward firmado

Este procedimiento es obligatorio para un defecto de aplicación publicado. No autoriza downgrade automático ni reutilización de binarios, firmas o evidencia. El último instalador estable puede permanecer disponible para recuperación manual documentada, pero la corrección distribuida es una versión superior firmada.

## Condiciones de entrada

- Incidente confirmado o sospecha razonable de daño, pérdida de función, seguridad, privacidad o actualización defectuosa.
- Acceso de `release approver` al canal de actualización y a los environments protegidos.
- Trazabilidad del tag, asset y hashes de la versión afectada.

## Checklist ejecutable

| Paso | Acción | Responsable | Evidencia obligatoria | Condición bloqueante |
| ---: | --- | --- | --- | --- |
| 1 | Congelar el canal de actualización y marcar la versión afectada como retirada sin borrar assets ni auditoría | `release approver` | Timestamp, actor, versión y estado del canal | No se puede demostrar el freeze; detener distribución y escalar |
| 2 | Abrir incidente con versión, commit, artifact-id, hashes, alcance, síntomas, datos en riesgo y criterio de recuperación | `author` | ID y registro inmutable del incidente | Falta identidad o criterio verificable |
| 3 | Identificar el último tag bueno mediante evidencia de release, no por fecha o memoria | `reviewer` | Tag, commit, SHA-256 firmado, matriz y aprobación originales | El tag no es inmutable o su evidencia no demuestra estado bueno |
| 4 | Crear una rama desde ese tag y revertir o corregir la causa mínima mediante Pull Request | `author` | Base de rama, diff, prueba roja y ledger del incidente | La rama no parte del tag bueno o amplía scope sin aprobación |
| 5 | Asignar una versión de parche superior a la defectuosa | `author` | Versionado y changelog enlazados al incidente | Se intenta reemplazar un tag/asset o usar una versión no superior |
| 6 | Reejecutar gate PR, revisión y branch protection sobre el nuevo commit | `reviewer` | Checks, aprobación y evidencia con SHA nuevo | Cualquier check falla o usa evidencia anterior |
| 7 | Construir una sola vez el nuevo NSIS y reejecutar release completo: instalación, inicio, audio/vídeo, datos, procesos y desinstalación | `reviewer` | Nuevo artifact-id, hashes y evidencia por etapa | Recompilación intermedia o caso requerido ausente |
| 8 | Enviar ese artefacto a SignPath, obtener aprobación y verificar Authenticode `Valid`, timestamp y publisher `SignPath Foundation` | `release approver` | Solicitud SignPath y SHA-256 signed | Firma, publisher, timestamp o hash no coincide |
| 9 | Publicar únicamente el nuevo hash firmado y validar recuperación contra el criterio del incidente | `release approver` | Asset, tag superior, validación y aprobación final | El defecto persiste o cualquier gate permanece abierto |
| 10 | Descongelar el canal y cerrar la fase de recuperación, preservando toda la auditoría | `release approver` | Timestamp, actor, versión activa y enlace al incidente | Falta validación post-publicación o aprobación humana |

## Fallos durante la recuperación

- Si falla un paso previo a publicación, el nuevo candidato no se publica y el canal permanece congelado.
- Si falla el parche publicado, el incidente se reabre y se repite este runbook desde el último tag que conserve evidencia de estado bueno.
- Nunca se fuerza un downgrade que pueda romper SQLite o divergir equipos.
- Toda migración SQLite crea respaldo, es idempotente y debe superar verificación de integridad antes de promoción.
- Una actualización de yt-dlp que falle checksum o health check no se promueve; se conserva la última versión verificada de forma atómica.
- Descargas y datos del usuario no se eliminan durante freeze, instalación, desinstalación o recuperación.

## Condición de salida

La recuperación termina solo cuando el parche superior firmado está publicado, el criterio del incidente pasa con evidencia fresca, el canal queda descongelado por aprobación humana y la auditoría conserva versiones, hashes y decisiones. En cualquier otro estado, `QA-GATE-ROLLFORWARD-001` permanece bloqueado.
