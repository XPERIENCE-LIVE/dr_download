/** @jest-environment node */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { writeDiagnosticReport } = require("../../diagnostics");

test("exports bounded local diagnostics with sensitive values redacted", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dr-download-diagnostics-"));
  const logs = path.join(root, "logs");
  const destination = path.join(root, "diagnostics.txt");
  fs.mkdirSync(logs);
  fs.writeFileSync(
    path.join(logs, "backend.log"),
    "failed https://example.com/video?token=secret at C:/Users/Wilder/private/cookies.db\n"
  );

  writeDiagnosticReport(logs, destination, { version: "2.1.0" });

  const report = fs.readFileSync(destination, "utf8");
  expect(report).toContain("Dr. Download diagnostics");
  expect(report).toContain("Version: 2.1.0");
  expect(report).toContain("[URL]");
  expect(report).toContain("[PRIVATE_PATH]");
  expect(report).not.toContain("secret");
  expect(report).not.toContain("Wilder");
});
