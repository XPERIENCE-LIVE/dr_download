/** @jest-environment node */
const { execFileSync, spawnSync } = require("node:child_process");
const path = require("node:path");
const script = path.resolve(__dirname, "../../scripts/playback-ui-smoke.mjs");

test("playback smoke self-check verifies strict duration and renderer request classification", () => {
  expect(execFileSync(process.execPath, [script, "--self-test"], { encoding: "utf8" }).trim()).toBe("Playback smoke self-check passed");
});

test.each(["NaN", "0", "-1", "3601", "1.5", "true"])("playback smoke rejects invalid duration %s before contacting an app", (duration) => {
  const result = spawnSync(process.execPath, [script, "9223", "isolated", "artifacts", "--duration=" + duration], { encoding: "utf8" });
  expect(result.status).not.toBe(0);
  expect(result.stderr).toContain("Duration must be an integer");
});
