import json
from pathlib import Path

from tools.contract_validator import validate_repository


SHA = "a" * 40
OTHER_SHA = "b" * 40
REQUIRED_CONTRACTS = (
    "README.md",
    "SECURITY.md",
    "PRIVACY.md",
    "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md",
    "docs/user-guide.md",
    "docs/product/epics.md",
    "docs/product/user-stories.md",
    "docs/product/acceptance-matrix.md",
    "docs/product/product-requirements.md",
    "docs/product/scope.md",
    "docs/product/success-criteria.md",
    "docs/architecture/architecture.md",
    "docs/architecture/technology-stack.md",
    "docs/architecture/api-contract.md",
    "docs/architecture/ipc-contract.md",
    "docs/architecture/state-machine.md",
    "docs/architecture/adr/ADR-001-runtime-engine.md",
    "docs/architecture/adr/ADR-002-output-directory-policy.md",
    "docs/design/design-system.md",
    "docs/design/error-copy.md",
    "docs/engineering/project-dna.md",
    "docs/qa/audits/2026-07-19-hierarchical-qa-audit.md",
    "docs/qa/traceability-matrix.md",
    "docs/qa/test-strategy.md",
    "docs/qa/manual-matrix.md",
    "docs/operations/diagnostics.md",
    "docs/operations/failure-modes.md",
    "docs/operations/rollback-runbook.md",
    "docs/release/windows-release.md",
    "docs/release/release-checklist.md",
    "docs/ai/kit-de-iniciacion.md",
    "docs/ai/guardrails.md",
    "docs/ai/definition-of-done.md",
    "docs/ai/implementation-task-template.md",
    "docs/ai/bugfix-task-template.md",
    "docs/ai/review-checklist.md",
    "docs/ai/change-ledger.json",
    "docs/superpowers/specs/2026-07-19-signpath-feedback-rollback-design.md",
    "docs/superpowers/plans/2026-07-19-qa-no-go-remediation.md",
)

COMPLETE_STORY = """# Historias

### US-010 — Inspeccionar

- **ID:** US-010
- **Épica:** E2
- **Persona:** usuario
- **Problema:** validar el medio
- **Precondiciones:** motor disponible
- **Flujo principal:** inspeccionar y mostrar
- **Flujos alternativos:** error estructurado
- **Given/When/Then:** Given un enlace, When se inspecciona, Then hay metadatos. Given un enlace inválido, When se rechaza, Then no se encola.
- **Prueba unitaria:** `test_inspect`.
- **Prueba de integración:** `test_inspect_api`.
- **Prueba E2E:** `MAN-US-010`.
- **Evidencia requerida:** `evidence/US-010.json`.
- **Riesgos:** red externa.
"""


def _matrix(state: str, *, sha: str = SHA) -> str:
    evidence = "evidence/US-010.json"
    return (
        "| Historia | Evidencia | Commit | Estado |\n"
        "|---|---|---|---|\n"
        f"| US-010 | {evidence} | {sha} | {state} |\n"
    )


def _write_evidence(root: Path, *, sha: str = SHA, result: str = "passed", approval: str = "approved"):
    path = root / "evidence/US-010.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "story_id": "US-010",
                "commit": sha,
                "result": result,
                "approval": approval,
            }
        ),
        encoding="utf-8",
    )


def make_repository(root: Path, *, story: str = COMPLETE_STORY, state: str = "partial") -> Path:
    for relative in REQUIRED_CONTRACTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.name}\n", encoding="utf-8")

    (root / "docs/product/epics.md").write_text("# Épicas\n\nUS-010\n", encoding="utf-8")
    (root / "docs/product/user-stories.md").write_text(story, encoding="utf-8")
    (root / "docs/product/acceptance-matrix.md").write_text(_matrix(state), encoding="utf-8")
    (root / "docs/qa/traceability-matrix.md").write_text(_matrix(state), encoding="utf-8")
    (root / "docs/qa/manual-matrix.md").write_text(
        "| ID | Historia | Precondición | Pasos | Resultado esperado | SO | Escala | Cookies | Ejecutor | Fecha | Estado | Evidencia |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        "| MAN-US-010 | US-010 | motor listo | inspeccionar URL | metadatos visibles | Windows 11 x64 | 100% | none | pending | pending | pending | pending |\n",
        encoding="utf-8",
    )
    (root / "docs/engineering/project-dna.md").write_text(
        "fail-closed\nSin fallbacks de producción.\nSin placeholders.\n"
        "Sin simulaciones como evidencia de aceptación o release.\n",
        encoding="utf-8",
    )
    (root / "docs/ai/change-ledger.json").write_text(
        json.dumps({"schema": 1, "changes": []}), encoding="utf-8"
    )
    (root / "backend/tests").mkdir(parents=True)
    (root / "backend/tests/test_inspection.py").write_text(
        "def test_inspect():\n    assert True\n\ndef test_inspect_api():\n    assert True\n",
        encoding="utf-8",
    )
    (root / "backend/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "electron/src/__tests__").mkdir(parents=True)
    (root / "electron/src/__tests__/inspection.test.js").write_text(
        "test('renders inspected media', () => expect(true).toBe(true));\n",
        encoding="utf-8",
    )
    (root / "electron/src/app.js").write_text("export const value = 1;\n", encoding="utf-8")
    return root


def test_complete_contract_repository_is_accepted(tmp_path: Path):
    root = make_repository(tmp_path)

    assert validate_repository(root) == []


def test_missing_normative_document_is_rejected(tmp_path: Path):
    root = make_repository(tmp_path)
    missing = root / "docs/product/scope.md"
    missing.unlink()

    errors = validate_repository(root)

    assert f"Falta el contrato obligatorio: {missing.as_posix()}" in errors


def test_missing_story_field_is_rejected(tmp_path: Path):
    root = make_repository(tmp_path, story=COMPLETE_STORY.replace("- **Riesgos:** red externa.\n", ""))

    errors = validate_repository(root)

    assert "US-010: falta el campo Riesgos" in errors


def test_each_given_when_then_scenario_must_be_complete(tmp_path: Path):
    story = COMPLETE_STORY.replace(
        "Given un enlace inválido, When se rechaza, Then no se encola.",
        "Given un enlace inválido, Then no se encola.",
    )
    root = make_repository(tmp_path, story=story)

    errors = validate_repository(root)

    assert "US-010: escenario 2 incompleto; requiere Given, When y Then en orden" in errors


def test_duplicate_story_id_is_rejected(tmp_path: Path):
    root = make_repository(tmp_path, story=COMPLETE_STORY + COMPLETE_STORY)

    errors = validate_repository(root)

    assert "ID de historia duplicado: US-010" in errors


def test_declared_python_test_must_exist_as_ast_symbol(tmp_path: Path):
    root = make_repository(tmp_path, story=COMPLETE_STORY.replace("test_inspect_api", "test_missing_api"))

    errors = validate_repository(root)

    assert "US-010: prueba declarada inexistente test_missing_api" in errors


def test_declared_jest_test_must_exist_as_executable_declaration(tmp_path: Path):
    story = COMPLETE_STORY.replace("`test_inspect_api`", "`missing renderer behavior`")
    root = make_repository(tmp_path, story=story)

    errors = validate_repository(root)

    assert "US-010: prueba Jest declarada inexistente missing renderer behavior" in errors


def test_story_missing_from_matrix_is_rejected(tmp_path: Path):
    root = make_repository(tmp_path)
    (root / "docs/qa/traceability-matrix.md").write_text(
        "| Historia | Evidencia | Commit | Estado |\n|---|---|---|---|\n",
        encoding="utf-8",
    )

    errors = validate_repository(root)

    assert "US-010: falta en matriz de trazabilidad" in errors


def test_duplicate_story_in_matrix_is_rejected(tmp_path: Path):
    root = make_repository(tmp_path)
    matrix = _matrix("partial")
    (root / "docs/product/acceptance-matrix.md").write_text(
        matrix + f"| US-010 | evidence/US-010.json | {SHA} | partial |\n",
        encoding="utf-8",
    )

    errors = validate_repository(root)

    assert "US-010: duplicada en matriz de aceptación" in errors


def test_manual_case_must_reference_its_declared_story(tmp_path: Path):
    root = make_repository(tmp_path)
    manual = (root / "docs/qa/manual-matrix.md").read_text(encoding="utf-8")
    (root / "docs/qa/manual-matrix.md").write_text(
        manual.replace("| MAN-US-010 | US-010 |", "| MAN-US-010 | US-999 |"),
        encoding="utf-8",
    )

    errors = validate_repository(root)

    assert "US-010: caso MAN-US-010 declara la historia US-999" in errors


def test_passed_manual_case_requires_real_approved_evidence(tmp_path: Path):
    root = make_repository(tmp_path)
    manual = (root / "docs/qa/manual-matrix.md").read_text(encoding="utf-8")
    (root / "docs/qa/manual-matrix.md").write_text(
        manual.replace("| pending | pending | pending | pending |", "| qa | 2026-07-19 | passed | pending |"),
        encoding="utf-8",
    )

    errors = validate_repository(root)

    assert "Matriz manual: MAN-US-010 passed sin evidencia real pending" in errors


def test_accepted_story_requires_approved_evidence_from_declared_commit(tmp_path: Path):
    root = make_repository(tmp_path, state="accepted")
    _write_evidence(root, sha=OTHER_SHA, approval="rejected")

    errors = validate_repository(root)

    assert f"US-010: evidencia pertenece a {OTHER_SHA}, no a {SHA}" in errors
    assert "US-010: evidencia no aprobatoria" in errors


def test_production_placeholder_is_rejected(tmp_path: Path):
    root = make_repository(tmp_path)
    (root / "backend/app.py").write_text("raise NotImplementedError('later')\n", encoding="utf-8")

    errors = validate_repository(root)

    assert "backend/app.py: implementación prohibida NotImplementedError" in errors


def test_embedded_python_download_engine_is_rejected(tmp_path: Path):
    root = make_repository(tmp_path)
    (root / "backend/app.py").write_text("import yt_dlp\n", encoding="utf-8")

    errors = validate_repository(root)

    assert "backend/app.py: implementación prohibida motor yt-dlp Python" in errors


def test_duplicate_change_id_is_rejected(tmp_path: Path):
    root = make_repository(tmp_path)
    entry = {
        "id": "BUG-001",
        "status": "open",
        "fingerprint": "same-root-cause-v1",
        "regression_tests": [],
        "evidence": [],
    }
    (root / "docs/ai/change-ledger.json").write_text(
        json.dumps({"schema": 1, "changes": [entry, entry]}), encoding="utf-8"
    )

    errors = validate_repository(root)

    assert "ID de cambio duplicado: BUG-001" in errors


def test_fixed_change_requires_existing_approved_evidence(tmp_path: Path):
    root = make_repository(tmp_path)
    (root / "docs/ai/change-ledger.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "changes": [
                    {
                        "id": "BUG-001",
                        "status": "fixed",
                        "fingerprint": "same-root-cause-v1",
                        "commit": SHA,
                        "regression_tests": ["test_inspect"],
                        "evidence": ["evidence/BUG-001.json"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    errors = validate_repository(root)

    assert "BUG-001: evidencia inexistente evidence/BUG-001.json" in errors


def test_verified_change_rejects_non_approving_evidence(tmp_path: Path):
    root = make_repository(tmp_path)
    path = root / "evidence/BUG-001.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"schema": 1, "commit": SHA, "result": "failed", "approval": "rejected"}),
        encoding="utf-8",
    )
    (root / "docs/ai/change-ledger.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "changes": [
                    {
                        "id": "BUG-001",
                        "status": "verified",
                        "fingerprint": "same-root-cause-v1",
                        "commit": SHA,
                        "regression_tests": ["test_inspect"],
                        "evidence": ["evidence/BUG-001.json"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    errors = validate_repository(root)

    assert "BUG-001: evidencia no aprobatoria evidence/BUG-001.json" in errors
