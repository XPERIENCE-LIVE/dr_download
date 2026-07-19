# Definition of Done

Una historia está `done` solo cuando todos los ítems aplicables están marcados y revisados. `accepted` exige además aprobación de release y evidencia real según `docs/engineering/project-dna.md`.

| Check | Responsable | Evidencia obligatoria | Condición bloqueante |
| --- | --- | --- | --- |
| Given/When/Then y alcance están completos, sin decisiones abiertas | `author` | Ficha de historia y diff del mismo SHA | Falta un escenario, criterio o decisión |
| Se observó una prueba roja antes del cambio de producción | `author` | Log con test exacto, SHA previo y fallo esperado | No existe rojo reproducible |
| La implementación mínima pasa la prueba y la regresión | `author` | Log verde del mismo SHA de la PR | Falla una prueba o el SHA no coincide |
| No hay fallbacks, placeholders ni simulaciones usadas como aceptación | `reviewer` | Revisión del diff y clasificación de pruebas | Existe una ruta degradada o evidencia simulada |
| Seguridad, privacidad, datos y errores accionables fueron revisados | `reviewer` | Checklist de revisión enlazada a la PR | Hay riesgo sin decisión aprobada |
| Documentación, ledger y matrices trazan el cambio | `author` | Rutas e IDs incluidos en la PR | Falta trazabilidad o un estado contradice la evidencia |
| Gate contractual y gate PR pasan el mismo commit | `reviewer` | Evidencia machine-readable con commit y exit code 0 | Un gate falla, falta o usa otro SHA |
| Branch protection y aprobación humana permiten integrar | `reviewer` | Estado de checks y aprobación de la PR | Push directo, check omitido o aprobación ausente |
| La evidencia de aceptación usa procesos y datos reales del nivel declarado | `reviewer` | Archivo de evidencia con versión, matriz y hashes | Evidencia parcial, antigua, simulada o de otro artefacto |
| Las 25 historias están aceptadas o existe reducción de scope aprobada | `release approver` | Matriz de aceptación o decisión de producto | Queda una historia requerida sin aceptación |
| El mismo instalador supera release gate, SignPath y post-firma | `release approver` | `release-artifact.json`, artifact-id, hashes y Authenticode `Valid` | Recompilación, publisher distinto o hash discordante |
| SBOM/licencias y Windows 10/11 están aprobados | `release approver` | SBOM, avisos y matriz manual firmada | Falta componente, licencia o caso requerido |
| La publicación se limita al hash firmado aprobado | `release approver` | Aprobación final y SHA-256 del asset | Asset distinto, tag mutable o automatización sin aprobación |

Un check bloqueado mantiene la historia o release fuera de `accepted`; no existe cierre condicional ni excepción implícita.
