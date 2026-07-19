# QA NO-GO Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir el NO-GO QA 36/100 en contratos ejecutables, evidencia ligada al artefacto y una cadena SignPath fail-closed sin publicar nada prematuramente.

**Architecture:** La remediación se divide en cuatro entregables independientes: gobierno documental ejecutable, higiene/gobierno GitHub, identidad de artefacto y recuperación runtime, y finalmente integración SignPath. Cada entregable conserva release bloqueada hasta que su evidencia exista; ninguna variable externa ausente se sustituye por un fallback.

**Tech Stack:** Python 3.13 stdlib/pytest, PowerShell 5.1, GitHub Actions, Electron 43/Node 22, React/Vite/Jest, FastAPI/SQLite, electron-builder NSIS, SignPath GitHub connector.

## Global Constraints

- Windows 10/11 x64; repositorio público MIT mientras se use SignPath Foundation.
- SignPath Foundation será el publisher visible.
- Un único artefacto se construye, prueba, firma y publica; está prohibido recompilar entre etapas.
- Todo cambio entra por Pull Request; `main` no admite push directo ni force-push.
- Sin fallbacks, placeholders, simulaciones de aceptación ni evidencia reutilizada de otro SHA.
- Rollback de aplicación por roll-forward firmado desde el último tag bueno.
- Ninguna release pública hasta Authenticode `Valid`, SBOM/licencias completos y 25 historias aceptadas o scope reducido mediante decisión aprobada.

---

### Task 1: Registrar el dictamen QA y hacerlo normativo

**Files:**
- Create: `docs/qa/audits/2026-07-19-hierarchical-qa-audit.md`
- Modify: `docs/engineering/project-dna.md`
- Modify: `docs/ai/guardrails.md`
- Modify: `docs/ai/definition-of-done.md`
- Modify: `docs/release/windows-release.md`
- Replace: `docs/operations/rollback-runbook.md`
- Modify: `docs/qa/test-strategy.md`

**Interfaces:**
- Consumes: veredicto supervisor NO-GO 36/100 y `docs/superpowers/specs/2026-07-19-signpath-feedback-rollback-design.md`.
- Produces: reglas normativas `QA-GATE-*` y procedimiento roll-forward verificable.

- [ ] **Step 1: Escribir el informe inmutable de auditoría**

Registrar fecha, rama, SHA base, scores 52/34/36, P0/P1 confirmados, falsos positivos descartados y criterios exactos de salida. No marcar ningún hallazgo como resuelto.

- [ ] **Step 2: Integrar feedback loop en el ADN**

Añadir reglas explícitas: artefacto único, evidencia por etapa, branch protection, aprobación humana, SignPath Foundation, publicación solo del hash firmado y roll-forward.

- [ ] **Step 3: Convertir DoD y rollback en checklists ejecutables**

Cada ítem debe indicar responsable (`author`, `reviewer`, `release approver`), evidencia y condición bloqueante. El runbook debe cubrir freeze, incidente, último tag bueno, nueva versión, reejecución completa y unfreeze.

- [ ] **Step 4: Ejecutar el validador documental actual**

Run: `python tools/contract_validator.py`  
Expected: PASS; este resultado solo prueba compatibilidad estructural previa a Task 2.

- [ ] **Step 5: Commit**

```powershell
git add docs/qa/audits docs/engineering/project-dna.md docs/ai docs/release/windows-release.md docs/operations/rollback-runbook.md docs/qa/test-strategy.md
git commit -m "docs: make QA feedback and rollback normative"
```

### Task 2: Endurecer el contrato SDD con TDD

**Files:**
- Modify: `tests/test_contract_validator.py`
- Modify: `tools/contract_validator.py`
- Modify: `docs/ai/change-ledger.json`
- Modify: `docs/product/user-stories.md`
- Modify: `docs/product/epics.md`
- Modify: `docs/product/acceptance-matrix.md`
- Modify: `docs/qa/traceability-matrix.md`
- Replace: `docs/qa/manual-matrix.md`

**Interfaces:**
- Produces: `validate_repository(root: Path) -> list[str]` que valida el universo documental, GWT por escenario, pruebas exactas, estados y evidencia.

- [ ] **Step 1: Añadir pruebas rojas del falso verde**

Crear fixtures temporales que demuestren fallo cuando falta un documento normativo, un escenario no tiene `When`, una prueba declarada no existe, un ledger `fixed` cita evidencia inexistente, una historia falta en matrices o un estado `accepted` usa evidencia de otro SHA.

- [ ] **Step 2: Confirmar rojo**

Run: `python -m pytest tests/test_contract_validator.py -q`  
Expected: FAIL en los nuevos casos por validación ausente.

- [ ] **Step 3: Implementar validación mínima con stdlib**

Ampliar la lista de documentos requeridos, construir el inventario de funciones `test_*` desde AST Python y texto Jest, analizar cada ficha entre encabezados `## US-###`, exigir Given/When/Then por criterio y validar filas únicas/estados/evidencia JSON.

- [ ] **Step 4: Corregir deriva documental real**

Renombrar las siete referencias de pruebas a símbolos existentes o crear historias/pruebas con TDD. Completar los tres `When`. Añadir historias para shutdown backend, accesibilidad, ES/EN y conservación de descargas al desinstalar, con filas individuales en ambas matrices.

- [ ] **Step 5: Convertir la matriz manual en casos ejecutables**

Definir IDs, precondición, pasos, resultado, sistema/escala/cookies, ejecutor, fecha, estado y ruta de evidencia para cada combinación declarada.

- [ ] **Step 6: Confirmar verde y regresión**

Run: `python -m pytest tests/test_contract_validator.py -q`  
Expected: PASS.  
Run: `python tools/contract_validator.py`  
Expected: PASS sin aceptar historias sin evidencia.

- [ ] **Step 7: Commit**

```powershell
git add tools/contract_validator.py tests/test_contract_validator.py docs/product docs/qa docs/ai/change-ledger.json
git commit -m "test: enforce complete SDD traceability"
```

### Task 3: Higiene Git y gobierno verificable

**Files:**
- Modify: `.gitignore`
- Create: `.gitattributes`
- Create: `.github/CODEOWNERS`
- Modify: `.github/workflows/quality-pr.yml`
- Modify: `.github/workflows/quality-release.yml`
- Modify: `.github/workflows/nightly-real.yml`
- Modify: `tests/test_quality_gate_scripts.py`

**Interfaces:**
- Produces: repositorio sin artefactos locales seleccionables y workflows con permisos mínimos/acciones fijadas por SHA.

- [ ] **Step 1: Añadir pruebas rojas de gobierno**

Exigir CODEOWNERS para workflows/policies/ADN/security; acciones con SHA hexadecimal de 40 caracteres; `permissions: contents: read`; ningún `CSC_*`; ningún artefacto local conocido visible por `git status --short`.

- [ ] **Step 2: Confirmar rojo**

Run: `python -m pytest tests/test_quality_gate_scripts.py -q`  
Expected: FAIL por CODEOWNERS ausente, tags móviles y CSC.

- [ ] **Step 3: Endurecer archivos Git**

Ignorar `.audit-*`, `.codebase-memory/`, `.package-test-data/`, `.superpowers/`, `config.json`, `*.bak`, `electron/resources/node/`, `electron/resources/ffmpeg/`, `electron/release-qa*/` y artefactos de smoke. Normalizar texto con `.gitattributes` sin reescritura masiva.

- [ ] **Step 4: Fijar acciones y permisos**

Resolver cada release oficial a SHA, fijar referencias, declarar permisos mínimos y CODEOWNERS. El workflow release deja de usar PFX/CSC; mientras SignPath no esté configurado debe fallar antes de publicar, no generar éxito degradado.

- [ ] **Step 5: Confirmar verde**

Run: `python -m pytest tests/test_quality_gate_scripts.py -q`  
Expected: PASS.  
Run: `git status --short`  
Expected: ningún runtime, descarga, configuración privada ni evidencia local fuera del alcance.

- [ ] **Step 6: Commit**

```powershell
git add .gitignore .gitattributes .github tests/test_quality_gate_scripts.py
git commit -m "ci: protect source and pin workflow supply chain"
```

### Task 4: Identidad explícita del artefacto y evidencia por etapa

**Files:**
- Modify: `tools/quality-gate.ps1`
- Modify: `tools/validate-release.ps1`
- Create: `tools/write-release-evidence.ps1`
- Modify: `electron/scripts/run-packaged-ui-smoke.ps1`
- Create: `electron/scripts/run-installed-smoke.ps1`
- Modify: `tests/test_quality_gate_scripts.py`

**Interfaces:**
- `validate-release.ps1 -InstallerPath <absolute-path> -ExpectedPublisher <string> -RequireSignature <bool>`.
- `release-artifact.json`: schema, commit, tag, run, artifact_id, unsigned_sha256, signed_sha256, publisher, timestamp_status, stages y exit codes.

- [ ] **Step 1: Añadir pruebas rojas**

Exigir ruta explícita, rechazo de instalador no coincidente, evidencia de cada etapa, duración/tipos FFprobe e instalación/desinstalación del NSIS.

- [ ] **Step 2: Confirmar rojo**

Run: `python -m pytest tests/test_quality_gate_scripts.py -q`  
Expected: FAIL por selección “más reciente” y ausencia de contrato instalado.

- [ ] **Step 3: Implementar validación determinista**

Eliminar selección por timestamp. Registrar hash unsigned; tras SignPath registrar hash signed y verificar publisher `SignPath Foundation`, firma `Valid` y timestamp válido.

- [ ] **Step 4: Probar el instalador exacto**

Instalar silenciosamente en directorio aislado, iniciar la app instalada, ejecutar smoke, validar audio/video con duración >0 y codec type esperado, desinstalar y comprobar preservación de descargas.

- [ ] **Step 5: Confirmar verde local interno**

La validación interna puede probar NSIS sin exigir firma, pero debe registrar `publishable: false`. Solo la etapa post-SignPath puede producir `publishable: true`.

- [ ] **Step 6: Commit**

```powershell
git add tools electron/scripts tests/test_quality_gate_scripts.py
git commit -m "test: bind release evidence to one installer"
```

### Task 5: Recuperación runtime fail-closed

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_engine_updater.py`
- Modify: `backend/tests/test_store.py`
- Modify: `electron/src/__tests__/app-updater.test.js`
- Modify: `backend/main.py`
- Modify: `backend/engine_updater.py`
- Modify: `backend/store.py`
- Modify: `electron/app-updater.js`

**Interfaces:**
- Backend aborta startup si `DR_DOWNLOAD_TOKEN` falta.
- `recover_previous_engine(data_dir) -> Path | None` restaura solo una versión verificada.
- SQLite mantiene `schema_version`, backup previo e integrity check.
- Updater devuelve errores estructurados y nunca usa catch vacío.

- [ ] **Step 1: Escribir pruebas rojas de token, crash y corrupción**
- [ ] **Step 2: Confirmar rojo con pytest/Jest focalizados**
- [ ] **Step 3: Implementar correcciones mínimas en fronteras compartidas**
- [ ] **Step 4: Confirmar verde focalizado y regresión completa**
- [ ] **Step 5: Commit**

```powershell
git add backend electron/app-updater.js electron/src/__tests__/app-updater.test.js
git commit -m "fix: fail closed and recover verified runtime state"
```

### Task 6: SBOM, manifiesto de runtimes y licencias

**Files:**
- Create: `tools/generate-sbom.ps1`
- Create: `electron/resources/runtime-manifest.json`
- Modify: `tools/validate-release.ps1`
- Modify: `THIRD_PARTY_NOTICES.md`
- Modify: `docs/release/release-checklist.md`
- Modify: `tests/test_quality_gate_scripts.py`

**Interfaces:**
- `runtime-manifest.json` fija nombre, versión, origen, licencia y SHA-256 de Node, FFmpeg, FFprobe y backend.
- Release produce CycloneDX JSON para Node/Python y bloquea divergencias.

- [ ] **Step 1: Añadir prueba roja para manifiesto/SBOM/licencias**
- [ ] **Step 2: Generar manifiesto con hashes reales y bundle de licencias**
- [ ] **Step 3: Bloquear release ante hash o aviso faltante**
- [ ] **Step 4: Confirmar verde y revisión legal documental**
- [ ] **Step 5: Commit**

```powershell
git add tools electron/resources/runtime-manifest.json THIRD_PARTY_NOTICES.md docs/release tests/test_quality_gate_scripts.py
git commit -m "build: verify runtime SBOM and licenses"
```

### Task 7: Integración SignPath y publicación manual

**Files:**
- Create: `.signpath/policies/dr-download/release-signing.yml`
- Modify: `.github/workflows/quality-release.yml`
- Modify: `README.md`
- Modify: `docs/release/windows-release.md`
- Modify: `docs/release/release-checklist.md`
- Modify: `tests/test_quality_gate_scripts.py`

**Interfaces:**
- Consumes secrets/variables externos reales: `SIGNPATH_API_TOKEN`, organization ID, project slug, signing policy slug y artifact configuration slug asignados tras admisión.
- Produces: signed workflow artifact y `release-artifact.json`; no publica GitHub Release automáticamente.

- [ ] **Step 1: Publicar Code signing policy, roles y privacidad**
- [ ] **Step 2: Añadir pruebas rojas del flujo artifact-id → SignPath → signed download**
- [ ] **Step 3: Integrar la acción SignPath fijada por SHA con permisos mínimos**
- [ ] **Step 4: Verificar tag sobre `main`, environment protegido y aprobación manual**
- [ ] **Step 5: Ejecutar en GitHub y adjuntar evidencia real**

Expected: mientras SignPath no admita el proyecto o falten variables, el job termina FAILED antes de publicación.

- [ ] **Step 6: Commit**

```powershell
git add .signpath .github README.md docs/release tests/test_quality_gate_scripts.py
git commit -m "ci: sign approved releases with SignPath"
```

### Task 8: Aceptación, PR y criterio de salida

**Files:**
- Modify: `docs/product/acceptance-matrix.md`
- Modify: `docs/qa/traceability-matrix.md`
- Modify: `docs/ai/change-ledger.json`
- Create: `evidence/<version>/...` only from real automated/manual runs.

- [ ] **Step 1: Ejecutar gate PR completo sobre SHA limpio**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/quality-gate.ps1 -Level pr`  
Expected: PASS, `commit` no nulo y hash ligado al SHA.

- [ ] **Step 2: Abrir PR y activar reglas externas**

Configurar `main`, CODEOWNERS, environment y checks requeridos; exportar evidencia de configuración.

- [ ] **Step 3: Ejecutar matriz real Windows 10/11**

Archivar cada caso con sistema, escala, cookies, ejecutor, fecha, hash y resultado.

- [ ] **Step 4: Ejecutar release firmado**

Expected: mismo artifact-id, firma `Valid`, publisher `SignPath Foundation`, instalación/smoke/desinstalación PASS.

- [ ] **Step 5: Cambiar estados solo con evidencia**

Ninguna historia pasa a `accepted` sin archivo real del mismo commit/version/matriz. `QUALITY-001` permanece abierto hasta que el release gate firmado sea verde.

- [ ] **Step 6: Solicitar revisión QA supervisora final**

Expected: score ≥90, cero P0/P1 y veredicto GO antes de publicar.
