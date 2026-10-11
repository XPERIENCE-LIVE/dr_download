const fs = require("fs");
const path = require("path");

const MAX_REPORT_BYTES = 2_000_000;

function redact(value) {
  return String(value)
    .replace(/https?:\/\/\S+/gi, "[URL]")
    .replace(/\b[A-Z]:[\\/]Users[\\/][^\\/\s]+(?:[\\/]\S*)?/gi, "[PRIVATE_PATH]")
    .replace(/\b(token|cookie|authorization)\s*[:=]\s*\S+/gi, "$1=[REDACTED]");
}

function writeDiagnosticReport(logDirectory, destination, metadata = {}) {
  const header = [
    "Dr. Download diagnostics",
    `Version: ${metadata.version || "unknown"}`,
    `Platform: ${metadata.platform || process.platform} ${metadata.arch || process.arch}`,
    ""
  ];
  let report = `${header.join("\n")}\n`;
  if (fs.existsSync(logDirectory)) {
    const names = fs.readdirSync(logDirectory)
      .filter((name) => /^backend\.log(?:\.\d+)?$/.test(name))
      .sort();
    for (const name of names) {
      const remaining = MAX_REPORT_BYTES - Buffer.byteLength(report);
      if (remaining <= 0) break;
      const content = fs.readFileSync(path.join(logDirectory, name), "utf8");
      report += `\n--- ${name} ---\n${redact(content).slice(-remaining)}`;
    }
  }
  fs.writeFileSync(destination, report, { encoding: "utf8", mode: 0o600 });
  return destination;
}

module.exports = { redact, writeDiagnosticReport };
