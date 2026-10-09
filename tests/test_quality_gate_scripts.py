import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTION_PINS = {
    "actions/checkout": "34e114876b0b11c390a56381ad16ebd13914f8d5",
    "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/setup-node": "49933ea5288caeca8642d1e84afbd3f7d6820020",
    "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
}


def read(path: str | Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def workflow_paths(root: Path = ROOT) -> tuple[str, ...]:
    directory = root / ".github" / "workflows"
    paths = sorted((*directory.glob("*.yml"), *directory.glob("*.yaml")))
    return tuple(path.relative_to(root).as_posix() for path in paths)


def workflow_job_blocks(workflow: str) -> list[str]:
    jobs = workflow.split("jobs:\n", 1)[1]
    starts = list(re.finditer(r"(?m)^  [a-zA-Z0-9_-]+:\s*$", jobs))
    return [
        jobs[match.start() : starts[index + 1].start() if index + 1 < len(starts) else None]
        for index, match in enumerate(starts)
    ]


def test_pr_gate_executes_every_required_validator_without_skip_switches():
    script = read("tools/quality-gate.ps1")

    assert "ValidateSet(\"pr\", \"release\")" in script
    assert "tools/contract_validator.py" in script
    assert "python -m pip check" in script
    assert "python -m pytest -q" in script
    assert "jest.js --runInBand" in script
    assert "npm --prefix electron run lint" in script
    assert "npm --prefix electron run build" in script
    assert "npm audit --prefix electron --audit-level=high" in script
    assert "Skip" not in script
    assert "workspace_sha256" in script
    assert '"electron/scripts"' in script
    assert "UTF8Encoding($false)" in script
    assert "COMPUTERNAME" not in script


def test_release_gate_is_a_strict_superset_with_real_artifact_checks():
    script = read("tools/quality-gate.ps1")
    release = read("tools/validate-release.ps1")

    assert "npm --prefix electron run package:win" in script
    assert "npm --prefix electron run smoke:packaged-ui" in script
    assert "tools/validate-release.ps1" in script
    assert "& powershell" not in script
    assert "Get-AuthenticodeSignature" in release
    assert 'Status -ne "Valid"' in release
    assert "Get-FileHash" in release
    assert 'Algorithm SHA256' in release
    assert "ffprobe.exe" in release
    assert "node.exe" in release
    assert "dr-download-backend.exe" in release


def test_pr_workflow_uses_windows_and_declared_runtime_versions():
    workflow = read(".github/workflows/quality-pr.yml")

    assert "runs-on: windows-latest" in workflow
    assert "python-version: '3.13'" in workflow
    assert "node-version: '22'" in workflow
    assert "npm ci --prefix electron" in workflow
    assert "tools/quality-gate.ps1 -Level pr" in workflow
    assert f"actions/checkout@{ACTION_PINS['actions/checkout']} # v4" in workflow


def test_release_workflow_requires_protected_environment_and_fails_closed_without_signpath():
    workflow = read(".github/workflows/quality-release.yml")

    assert "environment: production-release" in workflow
    expected_sources = {
        "SIGNPATH_ORGANIZATION_ID": "${{ vars.SIGNPATH_ORGANIZATION_ID }}",
        "SIGNPATH_PROJECT_SLUG": "${{ vars.SIGNPATH_PROJECT_SLUG }}",
        "SIGNPATH_SIGNING_POLICY_SLUG": "${{ vars.SIGNPATH_SIGNING_POLICY_SLUG }}",
        "SIGNPATH_API_TOKEN": "${{ secrets.SIGNPATH_API_TOKEN }}",
    }
    for name, source in expected_sources.items():
        assert f"{name}: {source}" in workflow
        assert f"{name} = $env:{name}" in workflow

    assert "$missing.Count -gt 0" in workflow
    assert "Sort-Object" in workflow
    assert 'throw "Release blocked: missing SignPath configuration: $($missing -join \', \')"' in workflow
    assert "Task 7" not in workflow
    assert "continue-on-error: true" not in workflow
    assert workflow.index("$missing.Count -gt 0") < workflow.index("tools/quality-gate.ps1 -Level release")
    assert workflow.index("tools/quality-gate.ps1 -Level release") < workflow.index("actions/upload-artifact@")
    assert "release" not in workflow.split("permissions:", 1)[1].split("jobs:", 1)[0]


def test_workflow_discovery_includes_yml_and_yaml(tmp_path: Path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "one.yml").write_text("name: one\n", encoding="utf-8")
    (workflows / "two.yaml").write_text("name: two\n", encoding="utf-8")
    (workflows / "ignored.txt").write_text("not a workflow\n", encoding="utf-8")

    assert workflow_paths(tmp_path) == (
        ".github/workflows/one.yml",
        ".github/workflows/two.yaml",
    )


def test_codeowners_protects_governance_release_and_sensitive_code():
    codeowners = read(".github/CODEOWNERS")

    for protected_path in (
        "/.github/workflows/",
        "/.signpath/",
        "/SECURITY.md",
        "/PRIVACY.md",
        "/docs/engineering/project-dna.md",
        "/docs/release/",
        "/docs/operations/rollback-runbook.md",
        "/backend/",
        "/electron/",
        "/tools/",
    ):
        assert re.search(
            rf"(?m)^{re.escape(protected_path)}\s+@PROGRESSIAGLOBALGROUP\s*$",
            codeowners,
        ), protected_path


def test_every_workflow_action_is_pinned_to_the_reviewed_commit():
    seen: set[str] = set()

    for path in workflow_paths():
        workflow = read(path)
        for action, revision in re.findall(r"(?m)^\s*-\s+uses:\s+([^@\s]+)@([0-9a-fA-F]+)", workflow):
            assert re.fullmatch(r"[0-9a-f]{40}", revision), f"{path}: {action}@{revision}"
            assert ACTION_PINS.get(action) == revision, f"{path}: unreviewed {action}@{revision}"
            seen.add(action)

        all_uses = re.findall(r"(?m)^\s*-\s+uses:\s+([^\s#]+)", workflow)
        assert all(re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", use) for use in all_uses), path

    assert seen == set(ACTION_PINS)


def test_workflows_declare_read_only_permissions_globally_and_per_job():
    for path in workflow_paths():
        workflow = read(path)
        assert re.search(r"(?m)^permissions:\n  contents: read\s*$", workflow), path
        assert "write-all" not in workflow
        blocks = workflow_job_blocks(workflow)
        assert blocks
        for block in blocks:
            assert re.search(r"(?m)^    permissions:\n      contents: read\s*$", block), path


def test_workflows_never_receive_direct_code_signing_secrets():
    workflows = "\n".join(read(path) for path in workflow_paths())

    for forbidden in ("CSC_LINK", "CSC_KEY_PASSWORD", ".pfx", ".p12", "PFX"):
        assert forbidden.lower() not in workflows.lower()


def test_local_artifacts_are_ignored_without_hiding_source_or_docs():
    ignored = (
        ".audit-example/file.json",
        ".codebase-memory/graph.db",
        ".package-test-data/case.bin",
        ".superpowers/sdd/report.md",
        "config.json",
        "backend/history.json.bak",
        "electron/resources/node/node.exe",
        "electron/resources/ffmpeg/ffmpeg.exe",
        "electron/resources/backend/dr-download-backend.exe",
        "electron/release-qa2/Dr-Download.exe",
        ".smoke-downloads/result.mp3",
        "electron/test-artifacts/packaged-smoke-123/result.json",
        "electron/test-artifacts/manual-smoke/evidence.json",
        "artifacts/quality/pr-evidence.json",
    )
    visible = ("backend/main.py", "docs/product/product-requirements.md", "SECURITY.md")

    for path in ignored:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", path],
            cwd=ROOT,
            check=False,
        )
        assert result.returncode == 0, path
    for path in visible:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", path],
            cwd=ROOT,
            check=False,
        )
        assert result.returncode == 1, path


def test_gitattributes_normalizes_text_and_marks_release_binaries():
    attributes = read(".gitattributes")

    assert "* text=auto" in attributes
    assert "/.gitattributes text eol=lf" in attributes
    assert "/.gitignore text eol=lf" in attributes
    assert "*.ps1 text eol=crlf" in attributes
    assert "*.cmd text eol=crlf" in attributes
    assert "*.yml text eol=lf" in attributes
    assert "*.py text eol=lf" in attributes
    for extension in ("exe", "dll", "png", "ico", "zip", "db"):
        assert f"*.{extension} binary" in attributes


def test_nightly_workflow_runs_the_real_packaged_smoke():
    workflow = read(".github/workflows/nightly-real.yml")

    assert "schedule:" in workflow
    assert "npm --prefix electron run package:win" in workflow
    assert "npm --prefix electron run smoke:packaged-ui" in workflow
    assert "windows-latest" in workflow


def test_packaged_smoke_downloads_audio_and_video_and_validates_streams():
    smoke = read("electron/scripts/packaged-ui-smoke.mjs")
    runner = read("electron/scripts/run-packaged-ui-smoke.ps1")

    assert '"audio-mp3", "video-best"' in smoke
    assert "stat(task.filename)" in smoke
    assert "ffprobe.exe" in runner
    assert "-show_entries" in runner
    assert '"/PID", "$($process.Id)", "/T", "/F"' in runner
    assert "dr-download-backend.exe" in runner
    assert "Packaged process remained after cleanup" in runner
