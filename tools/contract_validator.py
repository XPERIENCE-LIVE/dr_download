"""Executable SDD guardrails for Dr. Download."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date, datetime
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

STORY_STATES = {"partial", "blocked", "covered", "accepted"}
TERMINAL_MANUAL_STATES = {"passed", "failed"}
EXPLICIT_PENDING_VALUES = {"pending", "blocked"}
GENERIC_TERMINAL_VALUES = EXPLICIT_PENDING_VALUES | {"unknown", "unassigned", "none", "n/a"}
VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")


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


def _read_javascript_string(text: str, start: int) -> tuple[str | None, int]:
    quote = text[start]
    index = start + 1
    value = []
    dynamic_template = False
    escapes = {"n": "\n", "r": "\r", "t": "\t"}
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            following = text[index + 1]
            value.append(escapes.get(following, following))
            index += 2
            continue
        if quote == "`" and char == "$" and index + 1 < len(text) and text[index + 1] == "{":
            dynamic_template = True
        if char == quote:
            return (None if dynamic_template else "".join(value), index + 1)
        value.append(char)
        index += 1
    return None, len(text)


def _skip_javascript_trivia(text: str, start: int) -> int:
    index = start
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index + 2)
            index = len(text) if newline < 0 else newline + 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        break
    return index


def _read_javascript_regex(text: str, start: int) -> int:
    index = start + 1
    in_character_class = False
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            index += 2
            continue
        if char in "\r\n":
            return start + 1
        if char == "[" and not in_character_class:
            in_character_class = True
        elif char == "]" and in_character_class:
            in_character_class = False
        elif char == "/" and not in_character_class:
            index += 1
            while index < len(text) and text[index].isalpha():
                index += 1
            return index
        index += 1
    return len(text)


def _can_start_javascript_regex(previous: tuple[str, str] | None) -> bool:
    if previous is None:
        return True
    kind, value = previous
    if kind == "identifier":
        return value in {"return", "throw", "case", "yield", "await", "typeof", "void", "delete"}
    if kind == "literal":
        return False
    return value not in {")", "]", "}"}


def _jest_test_names(text: str) -> set[str]:
    names: set[str] = set()
    index = 0
    previous: tuple[str, str] | None = None
    while index < len(text):
        index = _skip_javascript_trivia(text, index)
        if index >= len(text):
            break
        char = text[index]
        if char in {"'", '"', "`"}:
            _, index = _read_javascript_string(text, index)
            previous = ("literal", "string")
            continue
        if char == "/" and _can_start_javascript_regex(previous):
            index = _read_javascript_regex(text, index)
            previous = ("literal", "regex")
            continue
        if char.isdigit():
            end = index + 1
            while end < len(text) and (text[end].isalnum() or text[end] in {".", "_"}):
                end += 1
            previous = ("literal", "number")
            index = end
            continue
        if char.isalpha() or char in {"_", "$"}:
            end = index + 1
            while end < len(text) and (text[end].isalnum() or text[end] in {"_", "$"}):
                end += 1
            identifier = text[index:end]
            following = _skip_javascript_trivia(text, end)
            is_global = previous is None or not (
                previous[0] == "identifier"
                or (previous[0] == "punctuation" and previous[1] in {".", "?."})
            )
            if (
                identifier in {"test", "it"}
                and is_global
                and following < len(text)
                and text[following] == "("
            ):
                argument = _skip_javascript_trivia(text, following + 1)
                if argument < len(text) and text[argument] in {"'", '"', "`"}:
                    name, argument_end = _read_javascript_string(text, argument)
                    if name is not None:
                        names.add(name)
                    index = argument_end
                    previous = ("literal", "string")
                    continue
            previous = ("identifier", identifier)
            index = end
            continue
        if text.startswith("?.", index):
            previous = ("punctuation", "?.")
            index += 2
            continue
        previous = ("punctuation", char)
        index += 1
    return names


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
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                python_symbols.add(node.name)
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                if any(
                    isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and method.name in {"__init__", "__new__"}
                    for method in node.body
                ):
                    continue
                for method in node.body:
                    if (
                        isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and method.name.startswith("test_")
                    ):
                        python_symbols.add(method.name)
    for pattern in ("*.test.js", "*.test.jsx"):
        for path in root.rglob(pattern):
            if set(path.relative_to(root).parts) & IGNORED_PARTS:
                continue
            jest_files.add(path.name)
            jest_files.add(path.relative_to(root).as_posix())
            jest_names.update(_jest_test_names(path.read_text(encoding="utf-8")))
    return python_symbols, jest_names, jest_files


def _declared_test_errors(
    story_id: str,
    value: str,
    python_symbols: set[str],
    jest_names: set[str],
    jest_files: set[str],
) -> list[str]:
    errors = []
    undelimited = re.sub(r"`[^`]*`", "", value)
    for reference in re.findall(r"\btest_[A-Za-z0-9_]+\b", undelimited):
        errors.append(f"{story_id}: referencia Python sin delimitar {reference}")
        if reference not in python_symbols:
            errors.append(f"{story_id}: prueba declarada inexistente {reference}")
    for reference in re.findall(r"`([^`]+)`", value):
        if re.fullmatch(r"test_[A-Za-z0-9_]+", reference):
            if reference not in python_symbols:
                errors.append(f"{story_id}: prueba declarada inexistente {reference}")
        elif re.search(r"\.test\.jsx?$", reference):
            if reference not in jest_files and Path(reference).name not in jest_files:
                errors.append(f"{story_id}: suite Jest declarada inexistente {reference}")
        elif " " in reference:
            if reference not in jest_names:
                errors.append(f"{story_id}: prueba Jest declarada inexistente {reference}")
        else:
            errors.append(f"{story_id}: referencia de prueba no clasificable {reference}")
    return errors


def _evaluated_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 2 or Path(lines[0]).resolve() != root.resolve():
        return None
    return lines[1] if re.fullmatch(r"[0-9a-f]{40}", lines[1]) else None


def _valid_iso_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _valid_iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return "T" in value


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
    evaluated_commit = _evaluated_commit(root)
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
    for label, rows, header in (
        ("matriz de aceptación", acceptance_rows, acceptance_header),
        ("matriz de trazabilidad", traceability_rows, traceability_header),
    ):
        for story_id, instances in sorted(rows.items()):
            if len(instances) > 1:
                errors.append(f"{story_id}: duplicada en {label}")
            for row in instances:
                state = _cell(header, row, "Estado").casefold()
                if state not in STORY_STATES:
                    errors.append(f"{story_id}: estado inválido {state or 'vacío'} en {label}")
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
        if evaluated_commit is None:
            errors.append(f"{story_id}: no se pudo determinar el commit del checkout")
        elif commit != evaluated_commit:
            errors.append(f"{story_id}: commit declarado {commit} no coincide con checkout {evaluated_commit}")
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
        "commit",
        "build",
        "estado",
        "evidencia",
    }
    if not required_manual_columns.issubset({item.casefold() for item in manual_header}):
        errors.append("Matriz manual: faltan columnas ejecutables obligatorias")
    manual_case_ids = [_cell(manual_header, row, "ID") for row in manual_rows]
    for case_id, count in Counter(manual_case_ids).items():
        if case_id and count > 1:
            errors.append(f"Matriz manual: ID duplicado {case_id}")
    manual_story_counts = Counter(_cell(manual_header, row, "Historia") for row in manual_rows)
    for story_id in sorted(actual_ids):
        if manual_story_counts[story_id] != 1:
            errors.append(f"{story_id}: no tiene exactamente un caso en matriz manual")
    for story_id in sorted(set(manual_story_counts) - actual_ids):
        if story_id:
            errors.append(f"Matriz manual: {story_id} no corresponde a una historia")
    for row in manual_rows:
        case_id = _cell(manual_header, row, "ID") or "caso sin ID"
        state = _cell(manual_header, row, "Estado").casefold()
        if state not in {"pending", "blocked", "passed", "failed"}:
            errors.append(f"Matriz manual: {case_id} tiene estado inválido {state or 'vacío'}")
        if any(not cell.strip() for cell in row):
            errors.append(f"Matriz manual: {case_id} contiene campos vacíos")
        if state in TERMINAL_MANUAL_STATES:
            executor = _cell(manual_header, row, "Ejecutor")
            execution_date = _cell(manual_header, row, "Fecha")
            commit = _cell(manual_header, row, "Commit").strip("`")
            build = _cell(manual_header, row, "Build")
            os_arch = _cell(manual_header, row, "SO").rsplit(" ", 1)
            evidence = _cell(manual_header, row, "Evidencia").strip("`")
            if executor.casefold() in GENERIC_TERMINAL_VALUES or len(executor.strip()) < 2:
                errors.append(f"Matriz manual: {case_id} {state} sin ejecutor real")
            if not _valid_iso_date(execution_date):
                errors.append(f"Matriz manual: {case_id} {state} sin fecha ISO-8601")
            if not re.fullmatch(r"[0-9a-f]{40}", commit):
                errors.append(f"Matriz manual: {case_id} {state} sin SHA completo")
            elif evaluated_commit is None:
                errors.append(f"Matriz manual: {case_id} no pudo determinar el commit del checkout")
            elif commit != evaluated_commit:
                errors.append(
                    f"Matriz manual: {case_id} commit {commit} no coincide con checkout {evaluated_commit}"
                )
            if not VERSION_PATTERN.fullmatch(build) or build == "0.0.0":
                errors.append(f"Matriz manual: {case_id} {state} sin build versionado")
            if len(os_arch) != 2:
                errors.append(f"Matriz manual: {case_id} SO no separa arquitectura")
            document, problem = _evidence_document(root / evidence)
            if problem:
                errors.append(f"Matriz manual: {case_id} {state} sin evidencia real {evidence}")
                continue
            if document.get("case_id") != case_id:
                errors.append(f"Matriz manual: {case_id} evidencia declara otro caso")
            if document.get("story_id") != _cell(manual_header, row, "Historia"):
                errors.append(f"Matriz manual: {case_id} evidencia declara otra historia")
            if document.get("commit") != commit:
                errors.append(f"Matriz manual: {case_id} evidencia declara otro commit")
            if document.get("build") != build:
                errors.append(f"Matriz manual: {case_id} evidencia declara otro build")
            if len(os_arch) == 2 and document.get("os") != os_arch[0]:
                errors.append(f"Matriz manual: {case_id} evidencia declara otro SO")
            if len(os_arch) == 2 and document.get("arch") != os_arch[1]:
                errors.append(f"Matriz manual: {case_id} evidencia declara otra arquitectura")
            if document.get("result") != state:
                errors.append(f"Matriz manual: {case_id} evidencia declara otro resultado")
            if document.get("approval") != "approved":
                errors.append(f"Matriz manual: {case_id} evidencia no aprobatoria")
        elif state in {"pending", "blocked"}:
            for field in ("Ejecutor", "Fecha", "Commit", "Build", "Evidencia"):
                if _cell(manual_header, row, field).casefold() not in EXPLICIT_PENDING_VALUES:
                    errors.append(f"Matriz manual: {case_id} {state} tiene {field} no ejecutado ambiguo")

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
                evidence_owners: dict[str, str] = {}
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
                    build = str(item.get("build") or "")
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
                    elif evaluated_commit is None:
                        errors.append(f"{change_id}: no se pudo determinar el commit del checkout")
                    elif commit != evaluated_commit:
                        errors.append(
                            f"{change_id}: commit declarado {commit} no coincide con checkout {evaluated_commit}"
                        )
                    if not VERSION_PATTERN.fullmatch(build):
                        errors.append(f"{change_id}: {status} sin build versionado")
                    approved_executions: set[str] = set()
                    for evidence in evidence_items:
                        evidence = str(evidence)
                        owner = evidence_owners.setdefault(evidence, change_id)
                        if owner != change_id:
                            errors.append(f"{change_id}: evidencia reutilizada por {owner} en {evidence}")
                        document, problem = _evidence_document(root / evidence)
                        if problem:
                            errors.append(f"{change_id}: evidencia inexistente {evidence}")
                            continue
                        if document.get("change_id") != change_id:
                            errors.append(
                                f"{change_id}: evidencia declara el cambio "
                                f"{document.get('change_id') or 'ausente'} en {evidence}"
                            )
                        if document.get("commit") != commit:
                            errors.append(f"{change_id}: evidencia de otro SHA {evidence}")
                        if document.get("build") != build:
                            errors.append(f"{change_id}: evidencia de otro build {evidence}")
                        if not _valid_iso_datetime(str(document.get("generated_at") or "")):
                            errors.append(f"{change_id}: evidencia sin generated_at ISO-8601 {evidence}")
                        if not _is_approving(document):
                            errors.append(f"{change_id}: evidencia no aprobatoria {evidence}")
                        executions = document.get("regression_tests")
                        if isinstance(executions, list):
                            for execution in executions:
                                if (
                                    isinstance(execution, dict)
                                    and execution.get("result") == "passed"
                                    and execution.get("approval") == "approved"
                                    and isinstance(execution.get("name"), str)
                                ):
                                    approved_executions.add(execution["name"])
                    if isinstance(regression_tests, list) and evidence_items:
                        evidence_label = str(evidence_items[0])
                        for reference in regression_tests:
                            if reference not in approved_executions:
                                errors.append(
                                    f"{change_id}: evidencia no acredita {reference} en {evidence_label}"
                                )

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
