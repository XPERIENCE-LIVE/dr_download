# Auditoría QA jerárquica — dictamen inmutable

Este documento conserva el dictamen recibido; no acredita remediación ni sustituye evidencia de ejecución.

## Identidad del dictamen

- Fecha: `2026-07-19`
- Rama auditada: `codex/signpath-feedback-loop`
- SHA base: `19c12aea5fa4c07b57766a689347dcb6d409d015`
- Plataforma objetivo: Windows 10/11 x64
- Resultado: **NO-GO**

| Capa de revisión | Score |
| --- | ---: |
| Evaluación inicial | 52/100 |
| Revisión adversarial | 34/100 |
| Dictamen supervisor | 36/100 |

Los scores son observaciones históricas de la revisión jerárquica. El único veredicto de salida vigente es el supervisor: `NO-GO 36/100`.

## P0 confirmados — abiertos

- `QA-P0-001`: ninguna de las 25 historias está en estado `accepted` con evidencia válida.
- `QA-P0-002`: `quality-release` terminó con `NotSigned` y no produjo `release-artifact.json`.
- `QA-P0-003`: los cambios y gates no están publicados; `origin/main` carece de branch protection o ruleset, environment protegido, tags y releases verificables.
- `QA-P0-004`: el workflow usa el modelo CSC; no existe integración SignPath ligada a artifact-id y origen verificable.
- `QA-P0-005`: el smoke usa `win-unpacked`; no instala, inicia ni desinstala el NSIS exacto, ni valida duración y tipo de streams.
- `QA-P0-006`: faltan SBOM, bundle de licencias Node, resolución documentada de obligaciones FFmpeg/GPL y Code Signing Policy con roles y atribución pública.

## P1/Important confirmados — abiertos

- `QA-P1-001`: el validador contractual omite documentos normativos, estados y evidencia.
- `QA-P1-002`: existe evidencia con commit nulo o hashes discordantes.
- `QA-P1-003`: siete referencias de pruebas no coinciden con símbolos ejecutables exactos.
- `QA-P1-004`: el token de backend puede operar fail-open; se clasifica `Important/P1`, no P0, porque Electron lo inyecta en el flujo empaquetado.
- `QA-P1-005`: el actualizador de aplicación silencia errores y no demuestra roll-forward.
- `QA-P1-006`: la actualización del motor no es crash-safe entre movimientos de archivos.
- `QA-P1-007`: SQLite no demuestra `integrity_check`, versión de esquema ni restauración.
- `QA-P1-008`: el instalador se selecciona por timestamp y no por identidad explícita.
- `QA-P1-009`: las GitHub Actions usan tags móviles y faltan CODEOWNERS y dependencias reproducibles.

## Falsos positivos descartados o acotados

- El ledger cumple su esquema mínimo actual; se descarta “ledger inexistente o inválido”, aunque su validación sigue siendo insuficiente (`QA-P1-001`).
- Existe rollback parcial del motor; se descarta “sin recuperación alguna”, pero su ventana no crash-safe sigue abierta (`QA-P1-006`).
- Un downgrade automático no es requisito y queda descartado: la recuperación normativa de aplicación es roll-forward firmado.
- El smoke sí valida parcialmente archivo y stream; se descarta “smoke sin validación”, sin alterar el P0 sobre el NSIS exacto (`QA-P0-005`).
- Los artefactos locales no ignorados son higiene P2, no un bloqueo P0/P1 por sí solos.

## Criterios exactos de salida — todos abiertos

No se autoriza una release pública hasta demostrar simultáneamente:

1. El gate PR completo pasa sobre un SHA limpio y su evidencia identifica ese mismo commit.
2. `main` rechaza push directo y force-push, exige Pull Request, CODEOWNERS, aprobación y checks; el environment de producción requiere aprobación humana.
3. Las 25 historias quedan `accepted` con evidencia real del mismo SHA, versión y matriz, o producto aprueba formalmente una reducción de scope.
4. La matriz real de Windows 10/11 está aprobada con ejecutor, fecha, configuración y evidencia por caso.
5. Un solo artifact-id recorre build, pruebas del instalador, SignPath y validación post-firma sin recompilación.
6. El NSIS exacto se instala, inicia, descarga/valida audio y vídeo, preserva datos y se desinstala; no deja procesos huérfanos.
7. El artefacto firmado tiene Authenticode `Valid`, publisher `SignPath Foundation`, timestamp válido y SHA-256 enlazado a toda la evidencia.
8. SBOM, licencias y avisos de terceros están completos y corresponden a los runtimes incluidos.
9. Un ensayo de incidente prueba freeze, rama desde el último tag bueno, parche superior, pipeline completo firmado y unfreeze autorizado.
10. Una revisión QA supervisora fresca obtiene score `>=90`, confirma cero P0/P1 abiertos y emite `GO`.

Toda afirmación anterior permanece **abierta** hasta que exista evidencia aprobada. Añadir contratos documentales no cambia por sí solo el estado de un hallazgo.
