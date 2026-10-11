const path = require("path");

function resolveRendererEntry(appDirectory, existsSync) {
  const entry = path.resolve(appDirectory, "dist", "public", "index.html");
  if (!existsSync(entry)) throw new Error("Compiled renderer entry is unavailable");
  return entry;
}

function resolveBackendCommand(isPackaged, resourcesPath, env, existsSync) {
  if (!isPackaged) {
    return { command: env.DR_DOWNLOAD_PYTHON || "python", args: ["-m", "backend.main"] };
  }
  const command = path.join(resourcesPath, "backend", "dr-download-backend.exe");
  if (!existsSync(command)) throw new Error("Packaged backend is unavailable");
  return { command, args: [] };
}

module.exports = { resolveBackendCommand, resolveRendererEntry };
