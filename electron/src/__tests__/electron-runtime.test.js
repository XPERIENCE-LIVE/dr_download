/** @jest-environment node */

const path = require("path");
const { resolveFfmpegDirectory, resolveNodeExecutable } = require("../../runtime-paths");
const { resolveBackendCommand, resolveRendererEntry } = require("../../runtime-contract");

test("uses bundled ffmpeg during development when no override is set", () => {
  expect(resolveFfmpegDirectory(false, "C:\\resources", "D:\\project", "")).toBe("D:\\project\\resources\\ffmpeg");
});

test("honors an explicit ffmpeg override", () => {
  expect(resolveFfmpegDirectory(false, "C:\\resources", "D:\\project", "E:\\ffmpeg")).toBe("E:\\ffmpeg");
});

test("uses the packaged Node runtime instead of a machine installation", () => {
  expect(resolveNodeExecutable(true, "C:/Program/Resources", "C:/Project", "C:/host/node.exe")).toBe(
    path.join("C:/Program/Resources", "node", "node.exe")
  );
});

test("uses the build Node runtime during development", () => {
  expect(resolveNodeExecutable(false, "C:/Program/Resources", "C:/Project", "C:/host/node.exe")).toBe(
    path.join("C:/Project", "resources", "node", "node.exe")
  );
});

test("loads only the canonical compiled renderer entry", () => {
  const expected = path.resolve("C:/Project", "dist", "public", "index.html");
  expect(resolveRendererEntry("C:/Project", (candidate) => candidate === expected)).toBe(expected);
});

test("fails closed when the canonical renderer entry is missing", () => {
  expect(() => resolveRendererEntry("C:/Project", () => false)).toThrow(
    "Compiled renderer entry is unavailable"
  );
});

test("fails closed when the packaged backend is missing", () => {
  expect(() => resolveBackendCommand(true, "C:/Resources", {}, () => false)).toThrow(
    "Packaged backend is unavailable"
  );
});

test("development backend uses only the declared Python command", () => {
  expect(resolveBackendCommand(false, "C:/Resources", { DR_DOWNLOAD_PYTHON: "py-final" }, () => false)).toEqual({
    command: "py-final",
    args: ["-m", "backend.main"]
  });
});
