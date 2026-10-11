const path = require("path");

function resolveFfmpegDirectory(isPackaged, resourcesPath, projectDir, override) {
  if (override) return override;
  return isPackaged ? path.join(resourcesPath, "ffmpeg") : path.join(projectDir, "resources", "ffmpeg");
}

function resolveNodeExecutable(isPackaged, resourcesPath, projectDir) {
  const root = isPackaged ? resourcesPath : path.join(projectDir, "resources");
  return path.join(root, "node", "node.exe");
}

module.exports = { resolveFfmpegDirectory, resolveNodeExecutable };
