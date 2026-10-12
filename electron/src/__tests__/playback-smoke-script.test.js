/** @jest-environment node */
const { execFileSync, spawnSync } = require("node:child_process");
const path = require("node:path");
const script = path.resolve(__dirname, "../../scripts/playback-ui-smoke.mjs");

(process.platform === "win32" ? test : test.skip)("launcher deadline permits ten continuous minutes for each provider", () => {
  const launcher = path.resolve(__dirname, "../../scripts/run-playback-ui-smoke.ps1").replace(/'/g, "''");
  const result = execFileSync("powershell", ["-NoProfile", "-Command", `
    $tokens = $null; $parseErrors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseFile('${launcher}', [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count) { throw 'Invalid launcher syntax' }
    $call = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst] -and $node.Member.Value -eq 'AddSeconds' }, $true)
    $Duration = 600
    Invoke-Expression $call.Arguments[0].Extent.Text
  `], { encoding: "utf8" });
  expect(Number(result.trim())).toBeGreaterThan(2 * 600);
});

test("playback smoke self-check verifies strict duration and renderer request classification", () => {
  expect(execFileSync(process.execPath, [script, "--self-test"], { encoding: "utf8" }).trim()).toBe("Playback smoke self-check passed");
});

test.each(["NaN", "0", "-1", "3601", "1.5", "true"])("playback smoke rejects invalid duration %s before contacting an app", (duration) => {
  const result = spawnSync(process.execPath, [script, "9223", "isolated", "artifacts", "--duration=" + duration], { encoding: "utf8" });
  expect(result.status).not.toBe(0);
  expect(result.stderr).toContain("Duration must be an integer");
});
