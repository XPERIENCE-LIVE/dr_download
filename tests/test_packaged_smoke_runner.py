import shutil
import subprocess
from pathlib import Path

import pytest


RUNNER = Path(__file__).resolve().parents[1] / "electron/scripts/run-packaged-ui-smoke.ps1"
POWERSHELL = shutil.which("powershell")
pytestmark = pytest.mark.skipif(not POWERSHELL, reason="Windows packaged smoke uses PowerShell")


def run_helper(body: str) -> subprocess.CompletedProcess:
    # Read the real functions without launching Electron or an installer.
    source = f"""$ErrorActionPreference = 'Stop'
$ast = [System.Management.Automation.Language.Parser]::ParseFile('{RUNNER.as_posix()}', [ref]$null, [ref]$null)
$functions = $ast.FindAll({{ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] }}, $false)
foreach ($function in $functions) {{ Invoke-Expression $function.Extent.Text }}
{body}
"""
    return subprocess.run([POWERSHELL, "-NoProfile", "-Command", source], capture_output=True, text=True, timeout=30)


def test_completed_file_must_stay_inside_its_isolated_download_directory(tmp_path):
    root = tmp_path.as_posix()
    result = run_helper(f"""Assert-ContainedFile '{root}/downloads' '{root}/downloads/result.mp3'
foreach ($outside in @('{root}/downloads-other/result.mp3', '{root}/downloads/../result.mp3')) {{
    $rejected = $false
    try {{ Assert-ContainedFile '{root}/downloads' $outside }} catch {{ $rejected = $true }}
    if (-not $rejected) {{ throw 'Accepted a file outside the isolated output directory' }}
}}
""")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("format_id,streams", [
    ("audio-mp3", '@(@{ codec_type = "audio"; codec_name = "mp3" })'),
    ("video-best", '@(@{ codec_type = "audio"; codec_name = "aac" }, @{ codec_type = "video"; codec_name = "h264" })'),
    ("video-compatible", '@(@{ codec_type = "audio"; codec_name = "aac" }, @{ codec_type = "video"; codec_name = "h264" })'),
])
def test_media_stream_checks_require_the_requested_audio_or_video(format_id, streams):
    result = run_helper(f"""Assert-MediaStreams '{format_id}' ([pscustomobject]@{{ streams = {streams} }})
foreach ($invalid in @(@(), @(@{{ codec_type = 'audio'; codec_name = 'opus' }}), @(@{{ codec_type = 'video'; codec_name = 'h264' }}))) {{
    $rejected = $false
    try {{ Assert-MediaStreams '{format_id}' ([pscustomobject]@{{ streams = $invalid }}) }} catch {{ $rejected = $true }}
    if (-not $rejected) {{ throw 'Accepted missing or incorrect requested streams' }}
}}
""")
    assert result.returncode == 0, result.stderr


def test_compatible_video_rejects_other_codecs():
    result = run_helper("""foreach ($codecs in @(@('vp9', 'aac'), @('h264', 'opus'))) {
    $probe = [pscustomobject]@{ streams = @(@{ codec_type = 'video'; codec_name = $codecs[0] }, @{ codec_type = 'audio'; codec_name = $codecs[1] }) }
    $rejected = $false
    try { Assert-MediaStreams 'video-compatible' $probe } catch { $rejected = $true }
    if (-not $rejected) { throw 'Compatible video accepted a different codec' }
}
""")
    assert result.returncode == 0, result.stderr


def test_runner_refuses_a_missing_explicit_installer_before_starting(tmp_path):
    missing = tmp_path / "explicit-installer.exe"
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-File", str(RUNNER), "-InstallerPath", str(missing)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "Required packaged artifact is unavailable" in result.stderr
    assert str(missing).replace(" ", "") in "".join(result.stderr.split())
