/** @jest-environment node */

const { buildApiRequest } = require("../../ipc-contract");


test("buildApiRequest exposes only declared backend operations", () => {
  expect(buildApiRequest("listDownloads", [])).toEqual({ method: "GET", path: "/downloads" });
  expect(buildApiRequest("cancelDownload", ["abc"])).toEqual({ method: "POST", path: "/downloads/abc/cancel" });
  expect(() => buildApiRequest("rawFetch", ["https://evil.test"])).toThrow("Unsupported operation");
});


test("buildApiRequest accepts bounded task identifiers", () => {
  expect(buildApiRequest("getDownload", ["abc-123"])).toEqual({ method: "GET", path: "/downloads/abc-123" });
});


test("buildApiRequest rejects malformed and oversized task identifiers", () => {
  expect(() => buildApiRequest("getDownload", ["../secret"])).toThrow("identifier");
  expect(() => buildApiRequest("cancelDownload", ["x".repeat(129)])).toThrow("identifier");
  expect(() => buildApiRequest("retryDownload", [null])).toThrow("identifier");
});


test("buildApiRequest rejects oversized inspection URLs", () => {
  expect(() => buildApiRequest("inspectMedia", [{
    url: `https://example.com/${"x".repeat(4096)}`,
    cookie_source: "none"
  }])).toThrow("URL");
});

test("buildApiRequest exposes directory validation", () => {
  expect(buildApiRequest("validateDirectory", [{ path: "C:\\Downloads" }])).toEqual({
    method: "POST",
    path: "/directories/validate",
    body: { path: "C:\\Downloads" }
  });
});
