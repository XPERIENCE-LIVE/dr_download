const path = require("path");


function resolveDownloadTarget(record, action) {
  if (!record || !["file", "folder"].includes(action)) throw new Error("Invalid file action");
  const output = path.resolve(String(record.output_dir || ""));
  if (!path.isAbsolute(output)) throw new Error("Invalid output folder");
  if (action === "folder") return output;
  if (!record.filename) throw new Error("Download has no recorded file");
  const filename = path.resolve(String(record.filename));
  const relative = path.relative(output, filename);
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("Recorded file is outside the authorized output folder");
  }
  return filename;
}


function sanitizeNotification(payload) {
  const clean = (value, limit) => String(value ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").slice(0, limit);
  return { title: clean(payload?.title, 80), body: clean(payload?.body, 240) };
}


module.exports = { resolveDownloadTarget, sanitizeNotification };
