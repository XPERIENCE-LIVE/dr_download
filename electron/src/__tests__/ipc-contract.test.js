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

test.each([-1, 1.5, true, "100", Number.MAX_SAFE_INTEGER + 1, Infinity])(
  "createDownload rejects invalid size estimate %p", (estimated_bytes) => {
    expect(() => buildApiRequest("createDownload", [{
      url: "https://example.com/video", format_id: "video-compatible", estimated_bytes
    }])).toThrow("estimate");
  }
);

test.each([0, 100, Number.MAX_SAFE_INTEGER, null, undefined])(
  "createDownload preserves optional advisory estimate %p", (estimated_bytes) => {
    const body = { url: "https://example.com/video", format_id: "video-compatible", estimated_bytes };
    expect(buildApiRequest("createDownload", [body]).body).toEqual(body);
  }
);

test.each(["137/best", "137+140", "best[ext=mp4]", "137,140", "(137)", " hls-2500", "137\n", "x".repeat(129)])(
  "createDownload rejects selector expression %p", (format_id) => {
    expect(() => buildApiRequest("createDownload", [{ url: "https://example.com/video", format_id }]))
      .toThrow("format");
  }
);

test.each(["video-compatible", "video-best", "audio-mp3", "audio-original", "137", "hls-2500"])(
  "createDownload accepts preset or extractor id %s", (format_id) => {
    expect(buildApiRequest("createDownload", [{ url: "https://example.com/video", format_id }]).body.format_id)
      .toBe(format_id);
  }
);
