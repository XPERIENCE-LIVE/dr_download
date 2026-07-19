/** @jest-environment node */

const path = require("path");
const { resolveDownloadTarget, sanitizeNotification } = require("../../file-actions");


test("file actions resolve only recorded files inside the authorized output folder", () => {
  const output = path.resolve("C:/Media");
  const filename = path.join(output, "video.mp4");

  expect(resolveDownloadTarget({ output_dir: output, filename }, "file")).toBe(filename);
  expect(resolveDownloadTarget({ output_dir: output, filename }, "folder")).toBe(output);
});


test("file actions reject recorded paths outside the authorized output folder", () => {
  expect(() => resolveDownloadTarget({
    output_dir: path.resolve("C:/Media"),
    filename: path.resolve("C:/Windows/System32/config.txt")
  }, "file")).toThrow("outside");
  expect(() => resolveDownloadTarget({ output_dir: "C:/Media" }, "unknown")).toThrow("action");
});


test("notifications are bounded and stripped of control characters", () => {
  const value = sanitizeNotification({
    title: `Dr\u0000 ${"x".repeat(200)}`,
    body: `Done\r\n${"y".repeat(500)}`
  });

  const hasNoControls = (text) => [...text].every((character) => {
    const code = character.charCodeAt(0);
    return code > 31 && code !== 127;
  });
  expect(hasNoControls(value.title)).toBe(true);
  expect(hasNoControls(value.body)).toBe(true);
  expect(value.title.length).toBeLessThanOrEqual(80);
  expect(value.body.length).toBeLessThanOrEqual(240);
});
