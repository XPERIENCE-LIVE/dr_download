# Definition of Done

Una historia está `done` solo cuando todos sus ítems aplicables están marcados y revisados. Cambia a `accepted` cuando la evidencia real de su propio nivel satisface sus criterios según `docs/engineering/project-dna.md`; no depende de una aprobación de release.

## Checklist de historia

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

Un check de historia bloqueado mantiene esa historia fuera de `accepted`; no existe cierre condicional ni excepción implícita.

## Checklist de release

La release solo se evalúa después de que las historias del alcance estén `accepted` o exista una reducción de scope aprobada. La aprobación de release no crea ni sustituye aceptación de historias.

| Check | Responsable | Evidencia obligatoria | Condición bloqueante |
| --- | --- | --- | --- |
| Todas las historias del alcance vigente están aceptadas o existe reducción de scope aprobada | `release approver` | Fichas y ambas matrices coincidentes, o decisión de producto | Queda una historia del universo derivado sin aceptación |
| El gate unsigned prueba el instalador exacto y registra `publishable: false` | `reviewer` | artifact-id, SHA-256 unsigned y resultados del gate | Se exige firma antes de SignPath, se prueba otro artefacto o falla un caso |
| SignPath devuelve el artefacto y el gate post-SignPath valida la firma | `release approver` | Solicitud, SHA-256 signed, timestamp, publisher y Authenticode `Valid` | Recompilación, firma ausente, publisher distinto o hash discordante |
| SBOM/licencias y Windows 10/11 están aprobados | `release approver` | SBOM, avisos y matriz manual firmada | Falta componente, licencia o caso requerido |
| La publicación se limita al hash firmado aprobado | `release approver` | Aprobación final y SHA-256 del asset | Asset distinto, tag mutable o automatización sin aprobación |

Un check de release bloqueado impide publicar, pero no altera retroactivamente la aceptación sustentada de una historia.
