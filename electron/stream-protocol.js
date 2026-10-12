const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const STREAM_URL = new RegExp(`^dr-stream://play/(${UUID})\\?start=([0-9]+(?:\\.[0-9]+)?)(?:&revision=([0-9]{1,10}))?$`, "i");

function parseStreamUrl(url) {
  const match = typeof url === "string" && url.length <= 2048 && !/[\r\n]/.test(url) && STREAM_URL.exec(url);
  if (!match || !Number.isFinite(Number(match[2])) || Number(match[3] || 0) > 2147483647) throw new Error("Invalid stream URL");
  return { sessionId: match[1], start: Number(match[2]), revision: Number(match[3] || 0) };
}

function streamError(status, code) {
  return Response.json({ detail: { code, message: "Stream unavailable.", recovery: "Reload the video." } }, {
    status, headers: { "Cache-Control": "no-store" }
  });
}

function createStreamHandler(baseUrl, sessionToken) {
  if (!/^http:\/\/127\.0\.0\.1:[0-9]+$/.test(baseUrl)) throw new Error("Invalid stream backend");
  return async (request) => {
    let sessionId;
    let start;
    let revision;
    try { ({ sessionId, start, revision } = parseStreamUrl(request.url)); }
    catch { return streamError(400, "invalid_stream_request"); }
    if (request.method !== "GET") return streamError(405, "invalid_stream_request");
    try {
      const upstream = await fetch(`${baseUrl}/playback/${sessionId}/stream?start=${start}&revision=${revision}`, {
        headers: { "X-Dr-Download-Token": sessionToken },
        signal: request.signal,
        cache: "no-store",
        redirect: "error"
      });
      const headers = new Headers({ "Cache-Control": "no-store" });
      for (const name of ["Content-Type", "X-Stream-Start"]) {
        if (upstream.headers.has(name)) headers.set(name, upstream.headers.get(name));
      }
      // Pass the body through: Chromium backpressure and cancellation reach fetch.
      return new Response(upstream.body, { status: upstream.status, headers });
    } catch {
      return streamError(502, "stream_unavailable");
    }
  };
}

module.exports = { createStreamHandler, parseStreamUrl };
