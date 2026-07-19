"""Executable SDD guardrails for Dr. Download."""

from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path


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

STORY_FIELDS = (
    "ID",
    "Épica",
    "Persona",
    "Problema",
    "Precondiciones",
    "Flujo principal",
    "Flujos alternativos",
    "Given/When/Then",
    "Prueba unitaria",
    "Prueba de integración",
    "Prueba E2E",
    "Evidencia requerida",
    "Riesgos",
)

PROHIBITED_PRODUCTION_PATTERNS = (
    (re.compile(r"\bNotImplementedError\b"), "NotImplementedError"),
    (re.compile(r"\b(?:TODO|FIXME)\b", re.IGNORECASE), "TODO/FIXME"),
    (re.compile(r"\bfallback\b", re.IGNORECASE), "fallback"),
    (re.compile(r"except\s+[^:]+:\s*(?:#[^\n]*\n\s*)?pass\b"), "except/pass"),
    (re.compile(r"catch\s*\([^)]*\)\s*\{\s*(?:/\*.*?\*/\s*)?\}"), "catch vacío"),
    (re.compile(r"data:text/plain", re.IGNORECASE), "pantalla data:text de sustitución"),
    (re.compile(r"^\s*(?:import|from)\s+yt_dlp\b", re.MULTILINE), "motor yt-dlp Python"),
)

IGNORED_PARTS = {
    ".git",
    ".pytest-tmp",
    ".venv",
    "node_modules",
    "dist",
    "release",
    "resources",
}


def _read(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"Falta el contrato obligatorio: {path.as_posix()}")
        return ""


def _story_sections(text: str) -> tuple[list[str], dict[str, str]]:
    matches = list(re.finditer(r"^###\s+(US-\d{3})\b.*$", text, re.MULTILINE))
    ids = [match.group(1) for match in matches]
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.setdefault(match.group(1), text[match.start():end])
    return ids, sections


def _field_value(section: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*\*\*{re.escape(field)}:\*\*\s*(.+)$", section, re.MULTILINE)
    return match.group(1).strip() if match else None


def _table(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [line for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return [], []
    header = [cell.strip() for cell in lines[0].strip().strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == len(header):
            rows.append(cells)
    return header, rows


def _story_matrix(text: str) -> tuple[dict[str, list[list[str]]], list[str]]:
    header, table_rows = _table(text)
    rows: dict[str, list[list[str]]] = {}
    for cells in table_rows:
        if cells and re.fullmatch(r"US-\d{3}", cells[0]):
            rows.setdefault(cells[0], []).append(cells)
    return rows, header


def _cell(header: list[str], row: list[str], name: str) -> str:
    folded = [item.casefold() for item in header]
    try:
        return row[folded.index(name.casefold())]
    except (ValueError, IndexError):
        return ""


def _test_inventory(root: Path) -> tuple[set[str], set[str], set[str]]:
    python_symbols: set[str] = set()
    jest_names: set[str] = set()
    jest_files: set[str] = set()
    for path in root.rglob("test*.py"):
        if set(path.relative_to(root).parts) & IGNORED_PARTS:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                python_symbols.add(node.name)
    for pattern in ("*.test.js", "*.test.jsx"):
        for path in root.rglob(pattern):
            if set(path.relative_to(root).parts) & IGNORED_PARTS:
                continue
            jest_files.add(path.name)
            jest_files.add(path.relative_to(root).as_posix())
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"\b(?:test|it)\s*\(\s*(['\"`])(.+?)\1\s*,", text, re.DOTALL):
                jest_names.add(match.group(2))
    return python_symbols, jest_names, jest_files


def _declared_test_errors(
    story_id: str,
    value: str,
    python_symbols: set[str],
    jest_names: set[str],
    jest_files: set[str],
) -> list[str]:
    errors = []
    for reference in re.findall(r"`([^`]+)`", value):
        if re.fullmatch(r"test_[A-Za-z0-9_]+", reference):
            if reference not in python_symbols:
                errors.append(f"{story_id}: prueba declarada inexistente {reference}")
        elif re.search(r"\.test\.jsx?$", reference):
            if reference not in jest_files and Path(reference).name not in jest_files:
                errors.append(f"{story_id}: suite Jest declarada inexistente {reference}")
        elif (
            " " in reference
            and "/" not in reference
            and "--" not in reference
            and re.match(r"^[a-z]", reference)
            and reference not in jest_names
        ):
            errors.append(f"{story_id}: prueba Jest declarada inexistente {reference}")
    return errors


def _evidence_document(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "invalid"
    return (document, None) if isinstance(document, dict) else (None, "invalid")


def _is_approving(document: dict) -> bool:
    return document.get("result") == "passed" and document.get("approval") == "approved"


def _production_files(root: Path):
    for base, patterns in ((root / "backend", ("*.py",)), (root / "electron", ("*.js", "*.jsx"))):
        if not base.exists():
            continue
        for pattern in patterns:
            for path in base.rglob(pattern):
                relative = path.relative_to(root)
                parts = set(relative.parts)
                if parts & (IGNORED_PARTS | {"tests", "__tests__"}):
                    continue
                if path.name.startswith("test_") or ".test." in path.name:
                    continue
                yield path


def validate_repository(root: Path) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    contracts = {relative: _read(root / relative, errors) for relative in REQUIRED_CONTRACTS}

    epics = contracts["docs/product/epics.md"]
    stories = contracts["docs/product/user-stories.md"]
    acceptance = contracts["docs/product/acceptance-matrix.md"]
    traceability = contracts["docs/qa/traceability-matrix.md"]
    manual = contracts["docs/qa/manual-matrix.md"]
    dna = contracts["docs/engineering/project-dna.md"]
    ledger_text = contracts["docs/ai/change-ledger.json"]

    expected_ids = set(re.findall(r"\bUS-\d{3}\b", epics))
    story_ids, sections = _story_sections(stories)
    counts = Counter(story_ids)
    for story_id, count in sorted(counts.items()):
        if count > 1:
            errors.append(f"ID de historia duplicado: {story_id}")
    actual_ids = set(story_ids)
    for story_id in sorted(expected_ids - actual_ids):
        errors.append(f"{story_id}: aparece en épicas pero no tiene ficha")
    for story_id in sorted(actual_ids - expected_ids):
        errors.append(f"{story_id}: tiene ficha pero no aparece en épicas")

    python_symbols, jest_names, jest_files = _test_inventory(root)
    manual_header, manual_rows = _table(manual)
    manual_ids = {_cell(manual_header, row, "ID") for row in manual_rows}
    manual_by_id = {_cell(manual_header, row, "ID"): row for row in manual_rows}
    for story_id, section in sorted(sections.items()):
        fields = {field: _field_value(section, field) for field in STORY_FIELDS}
        for field, value in fields.items():
            if not value:
                errors.append(f"{story_id}: falta el campo {field}")
        scenarios = re.split(r"(?=\bGiven\b)", fields.get("Given/When/Then") or "")
        scenarios = [scenario.strip() for scenario in scenarios if scenario.strip()]
        for index, scenario in enumerate(scenarios, 1):
            if not re.match(r"^Given\b.+\bWhen\b.+\bThen\b", scenario):
                errors.append(
                    f"{story_id}: escenario {index} incompleto; requiere Given, When y Then en orden"
                )
        for field in ("Prueba unitaria", "Prueba de integración"):
            errors.extend(
                _declared_test_errors(
                    story_id,
                    fields.get(field) or "",
                    python_symbols,
                    jest_names,
                    jest_files,
                )
            )
        for case_id in re.findall(r"\bMAN-US-\d{3}\b", fields.get("Prueba E2E") or ""):
            if case_id not in manual_ids:
                errors.append(f"{story_id}: caso manual inexistente {case_id}")
            elif _cell(manual_header, manual_by_id[case_id], "Historia") != story_id:
                errors.append(
                    f"{story_id}: caso {case_id} declara la historia "
                    f"{_cell(manual_header, manual_by_id[case_id], 'Historia')}"
                )

    acceptance_rows, acceptance_header = _story_matrix(acceptance)
    traceability_rows, traceability_header = _story_matrix(traceability)
    for label, rows in (
        ("matriz de aceptación", acceptance_rows),
        ("matriz de trazabilidad", traceability_rows),
    ):
        for story_id, instances in sorted(rows.items()):
            if len(instances) > 1:
                errors.append(f"{story_id}: duplicada en {label}")
        for story_id in sorted(actual_ids - set(rows)):
            errors.append(f"{story_id}: falta en {label}")
        for story_id in sorted(set(rows) - actual_ids):
            errors.append(f"{story_id}: aparece en {label} pero no tiene ficha")

    for story_id in sorted(actual_ids & set(acceptance_rows) & set(traceability_rows)):
        acceptance_row = acceptance_rows[story_id][0]
        traceability_row = traceability_rows[story_id][0]
        acceptance_state = _cell(acceptance_header, acceptance_row, "Estado").casefold()
        traceability_state = _cell(traceability_header, traceability_row, "Estado").casefold()
        if acceptance_state != traceability_state:
            errors.append(f"{story_id}: estado incoherente entre matrices")
        if "accepted" not in {acceptance_state, traceability_state}:
            continue
        evidence_values = {
            _cell(acceptance_header, acceptance_row, "Evidencia").strip("`"),
            _cell(traceability_header, traceability_row, "Evidencia").strip("`"),
        }
        commits = {
            _cell(acceptance_header, acceptance_row, "Commit").strip("`"),
            _cell(traceability_header, traceability_row, "Commit").strip("`"),
        }
        if len(evidence_values) != 1 or not next(iter(evidence_values), ""):
            errors.append(f"{story_id}: matrices accepted no comparten una evidencia")
            continue
        if len(commits) != 1 or not re.fullmatch(r"[0-9a-f]{40}", next(iter(commits), "")):
            errors.append(f"{story_id}: matrices accepted no comparten un SHA completo")
            continue
        evidence = next(iter(evidence_values))
        commit = next(iter(commits))
        document, problem = _evidence_document(root / evidence)
        if problem:
            errors.append(f"{story_id}: estado accepted sin evidencia real {evidence}")
            continue
        evidence_commit = str(document.get("commit") or "")
        if evidence_commit != commit:
            errors.append(f"{story_id}: evidencia pertenece a {evidence_commit or 'SHA ausente'}, no a {commit}")
        if document.get("story_id") != story_id:
            errors.append(f"{story_id}: evidencia declara otra historia")
        if not _is_approving(document):
            errors.append(f"{story_id}: evidencia no aprobatoria")

    required_manual_columns = {
        "id",
        "historia",
        "precondición",
        "pasos",
        "resultado esperado",
        "so",
        "escala",
        "cookies",
        "ejecutor",
        "fecha",
        "estado",
        "evidencia",
    }
    if not required_manual_columns.issubset({item.casefold() for item in manual_header}):
        errors.append("Matriz manual: faltan columnas ejecutables obligatorias")
    manual_case_ids = [_cell(manual_header, row, "ID") for row in manual_rows]
    for case_id, count in Counter(manual_case_ids).items():
        if case_id and count > 1:
            errors.append(f"Matriz manual: ID duplicado {case_id}")
    for row in manual_rows:
        case_id = _cell(manual_header, row, "ID") or "caso sin ID"
        state = _cell(manual_header, row, "Estado").casefold()
        if state not in {"pending", "blocked", "passed", "failed"}:
            errors.append(f"Matriz manual: {case_id} tiene estado inválido {state or 'vacío'}")
        if any(not cell.strip() for cell in row):
            errors.append(f"Matriz manual: {case_id} contiene campos vacíos")
        if state in {"passed", "failed"}:
            evidence = _cell(manual_header, row, "Evidencia").strip("`")
            document, problem = _evidence_document(root / evidence)
            if problem:
                errors.append(f"Matriz manual: {case_id} {state} sin evidencia real {evidence}")
                continue
            if document.get("case_id") != case_id:
                errors.append(f"Matriz manual: {case_id} evidencia declara otro caso")
            if document.get("story_id") != _cell(manual_header, row, "Historia"):
                errors.append(f"Matriz manual: {case_id} evidencia declara otra historia")
            if state == "passed" and not _is_approving(document):
                errors.append(f"Matriz manual: {case_id} evidencia no aprobatoria")

    dna_required = ("fail-closed", "sin fallbacks", "sin placeholders", "sin simulaciones como evidencia")
    folded_dna = dna.casefold()
    for rule in dna_required:
        if rule not in folded_dna:
            errors.append(f"ADN incompleto: falta la regla '{rule}'")

    for path in _production_files(root):
        text = path.read_text(encoding="utf-8")
        for pattern, label in PROHIBITED_PRODUCTION_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path.relative_to(root).as_posix()}: implementación prohibida {label}")

    if ledger_text:
        try:
            ledger = json.loads(ledger_text)
        except json.JSONDecodeError as exc:
            errors.append(f"change-ledger.json inválido: {exc.msg}")
        else:
            changes = ledger.get("changes") if isinstance(ledger, dict) else None
            if not isinstance(ledger, dict) or ledger.get("schema") != 1 or not isinstance(changes, list):
                errors.append("change-ledger.json: schema debe ser 1 y changes debe ser una lista")
            else:
                change_ids = [str(item.get("id") or "") for item in changes if isinstance(item, dict)]
                for change_id, count in sorted(Counter(change_ids).items()):
                    if change_id and count > 1:
                        errors.append(f"ID de cambio duplicado: {change_id}")
                fingerprints: dict[str, str] = {}
                for item in changes:
                    if not isinstance(item, dict):
                        errors.append("change-ledger.json: cada cambio debe ser un objeto")
                        continue
                    change_id = str(item.get("id") or "")
                    status = str(item.get("status") or "")
                    fingerprint = str(item.get("fingerprint") or "")
                    if not re.fullmatch(r"[A-Z][A-Z0-9-]{2,63}", change_id):
                        errors.append(f"ID de cambio inválido: {change_id or 'vacío'}")
                    if status not in {"open", "fixed", "verified", "reopened", "wont-fix"}:
                        errors.append(f"{change_id}: estado de cambio inválido {status or 'vacío'}")
                    if not fingerprint:
                        errors.append(f"{change_id}: falta fingerprint")
                    elif fingerprint in fingerprints and fingerprints[fingerprint] != change_id:
                        errors.append(
                            f"Fingerprint duplicado: {fingerprint} en {fingerprints[fingerprint]} y {change_id}"
                        )
                    else:
                        fingerprints[fingerprint] = change_id
                    if status not in {"fixed", "verified"}:
                        continue
                    regression_tests = item.get("regression_tests")
                    evidence_items = item.get("evidence")
                    commit = str(item.get("commit") or "")
                    if not isinstance(regression_tests, list) or not regression_tests:
                        errors.append(f"{change_id}: {status} sin prueba de regresión")
                    else:
                        for reference in regression_tests:
                            if (
                                reference not in python_symbols
                                and reference not in jest_names
                                and reference not in jest_files
                            ):
                                errors.append(f"{change_id}: prueba de regresión inexistente {reference}")
                    if not isinstance(evidence_items, list) or not evidence_items:
                        errors.append(f"{change_id}: {status} sin evidencia")
                        continue
                    if not re.fullmatch(r"[0-9a-f]{40}", commit):
                        errors.append(f"{change_id}: {status} sin SHA completo")
                    for evidence in evidence_items:
                        document, problem = _evidence_document(root / str(evidence))
                        if problem:
                            errors.append(f"{change_id}: evidencia inexistente {evidence}")
                            continue
                        if document.get("commit") != commit:
                            errors.append(f"{change_id}: evidencia de otro SHA {evidence}")
                        if not _is_approving(document):
                            errors.append(f"{change_id}: evidencia no aprobatoria {evidence}")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_repository(root)
    if errors:
        print("CONTRACT GATE: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("CONTRACT GATE: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
