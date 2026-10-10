# Quality Gates and Executable Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir las especificaciones SDD de Dr. Download en validadores y gates bloqueantes, eliminar rutas de ejecución alternativas silenciosas y separar evidencia de PR de evidencia comercial real.

**Architecture:** Un validador Python basado únicamente en la biblioteca estándar comprobará integridad documental, trazabilidad, marcadores prohibidos y evidencias aceptadas. Un único script PowerShell compondrá los comandos reales de PR y release; GitHub Actions invocará ese mismo script para evitar divergencia entre local y CI.

**Tech Stack:** Python 3.13, PowerShell 7/Windows PowerShell, Node.js 22, Jest, ESLint, Vite, Electron Builder, PyInstaller y GitHub Actions.

## Global Constraints

- Windows 10/11 x64 es la plataforma comercial.
- Ningún fallback silencioso, placeholder o implementación simulada puede existir en producción.
- Ningún mock, stub o simulación puede constituir evidencia de aceptación o release.
- Una incapacidad del runtime debe fallar de forma explícita, estructurada y accionable.
- El gate de release exige instalador real, smoke real, SHA-256 y Authenticode `Valid`.
- No se publica ni se modifica `main` mientras exista un gate pendiente o bloqueado.

---

### Task 1: Contract validator

**Files:**
- Create: `tools/contract_validator.py`
- Create: `tests/test_contract_validator.py`

**Interfaces:**
- Consumes: documentos Markdown del repositorio.
- Produces: `validate_repository(root: Path) -> list[str]` y CLI con código 0/1.

- [ ] Escribir pruebas que exijan IDs únicos, fichas completas, filas de aceptación/trazabilidad, evidencia para estados `accepted` y ausencia de marcadores prohibidos en producción.
- [ ] Ejecutar `python -m pytest tests/test_contract_validator.py -q` y observar fallos por módulo ausente.
- [ ] Implementar el parser mínimo con `pathlib` y `re`.
- [ ] Ejecutar la prueba focal y confirmar verde.

### Task 2: Project DNA and complete E1 stories

**Files:**
- Create: `docs/engineering/project-dna.md`
- Modify: `docs/ai/guardrails.md`
- Modify: `docs/ai/definition-of-done.md`
- Modify: `docs/ai/kit-de-iniciacion.md`
- Modify: `docs/product/user-stories.md`
- Modify: `docs/qa/test-strategy.md`
- Modify: `docs/qa/traceability-matrix.md`

**Interfaces:**
- Consumes: campos obligatorios definidos por el validador.
- Produces: contrato normativo completo para US-001 a US-053.

- [ ] Ejecutar el validador contra el repositorio y observar los campos faltantes de US-001..US-004.
- [ ] Completar las cuatro fichas sin cambiar comportamiento de producto.
- [ ] Definir `real evidence`, `controlled test double` y la prohibición de atribuir aceptación a simulaciones.
- [ ] Ejecutar el validador y confirmar que la documentación queda consistente.

### Task 3: Fail-closed runtime

**Files:**
- Modify: `backend/tests/test_engine_runner.py`
- Modify: `backend/tests/test_downloader.py`
- Modify: `backend/engine_runner.py`
- Modify: `backend/downloader.py`
- Modify: `electron/src/__tests__/electron-runtime.test.js`
- Modify: `electron/electron.js`
- Modify: `docs/architecture/architecture.md`
- Modify: `docs/architecture/adr/ADR-001-runtime-engine.md`

**Interfaces:**
- Consumes: runtime Node, yt-dlp y HTML compilado empaquetados.
- Produces: errores explícitos si falta cualquiera; una sola ruta de motor y una sola ruta de UI.

- [ ] Escribir pruebas rojas: Node ausente genera error; yt-dlp ausente falla tarea; HTML canónico ausente no carga data URL ni layout legado.
- [ ] Ejecutar pruebas focales y verificar el fallo esperado.
- [ ] Eliminar motor Python alternativo, resolución implícita de Node y layout HTML legado.
- [ ] Actualizar ADR y arquitectura.
- [ ] Ejecutar pruebas focales y regresión Python/Jest.

### Task 4: Local quality gates

**Files:**
- Create: `tools/quality-gate.ps1`
- Create: `tools/validate-release.ps1`
- Create: `tests/test_quality_gate_scripts.py`
- Modify: `package.json`
- Modify: `docs/qa/test-strategy.md`
- Modify: `docs/release/release-checklist.md`

**Interfaces:**
- Consumes: `-Level pr|release`.
- Produces: código de salida distinto de cero al primer fallo y evidencia JSON en `artifacts/quality/`.

- [ ] Escribir pruebas estructurales rojas que exijan todos los comandos y ausencia de opciones de omisión.
- [ ] Implementar un gate PR con contratos, pytest, Jest, lint y build.
- [ ] Implementar gate release como superconjunto con empaquetado, smoke, hash y firma.
- [ ] Ejecutar pruebas focales y el gate PR real.

### Task 5: GitHub Actions gates

**Files:**
- Replace: `.github/workflows/nodejs.yml`
- Replace: `.github/workflows/python.yml`
- Create: `.github/workflows/quality-pr.yml`
- Create: `.github/workflows/quality-release.yml`
- Create: `.github/workflows/nightly-real.yml`
- Modify: `docs/release/windows-release.md`

**Interfaces:**
- Consumes: eventos PR, manual, schedule y release.
- Produces: checks estables `quality-pr` y `quality-release`; artefactos de evidencia.

- [ ] Hacer que los workflows heredados dejen de duplicar lógica.
- [ ] Ejecutar PR gate en `windows-latest` con Python 3.13 y Node 22 usando `npm ci`.
- [ ] Ejecutar release real únicamente con secretos de firma configurados.
- [ ] Ejecutar smoke externo en schedule/manual, nunca como sustituto de PR.
- [ ] Validar YAML como texto contractual desde pytest.

### Task 6: Verification and repository handoff

**Files:**
- Modify: `docs/ai/change-ledger.md`
- Modify: `docs/qa/traceability-matrix.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: salida fresca de todos los gates.
- Produces: estado real, hash de evidencia y lista explícita de gates externos pendientes.

- [ ] Ejecutar `python tools/contract_validator.py`.
- [ ] Ejecutar `powershell -ExecutionPolicy Bypass -File tools/quality-gate.ps1 -Level pr`.
- [ ] Ejecutar el gate release y registrar el bloqueo esperado si Authenticode no es `Valid`.
- [ ] Comparar el workspace verificado con `XPERIENCE-LIVE/dr_download` en una rama, sin actualizar `main`.
- [ ] Abrir PR solo después de que la evidencia local sea verde y nunca fusionarlo con gates externos pendientes.

