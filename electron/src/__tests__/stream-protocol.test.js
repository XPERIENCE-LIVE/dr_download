/** @jest-environment node */

const http = require("http");
const fs = require("fs");
const path = require("path");
const { createStreamHandler, parseStreamUrl } = require("../../stream-protocol");

const id = "172f421c-70bf-4ec4-83a5-c242207eb9e0";
let server;
let baseUrl;
beforeEach(async () => {
  server = http.createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});
afterEach(async () => {
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
});

test("parses finite decimal seek and UUID without accepting other protocol operations", () => {
  expect(parseStreamUrl(`dr-stream://play/${id}?start=12.375`)).toEqual({ sessionId: id, start: 12.375, revision: 0 });
  expect(parseStreamUrl(`dr-stream://play/${id}?start=0`)).toEqual({ sessionId: id, start: 0, revision: 0 });
  expect(parseStreamUrl(`dr-stream://play/${id}?start=15.23&revision=7`)).toEqual({ sessionId: id, start: 15.23, revision: 7 });
});

test.each([
  `http://play/${id}?start=0`, `dr-stream://other/${id}?start=0`, `dr-stream://play/abc?start=0`,
  `dr-stream://play/${id}?start=-1`, `dr-stream://play/${id}?start=NaN`, `dr-stream://play/${id}?start=Infinity`,
  `dr-stream://play/${id}?start=0&token=x`, `dr-stream://play/${id}?start=0&start=1`,
  `dr-stream://play/${id}?start=0?start=1`, `dr-stream://play/${id}#fragment`,
  `dr-stream://play/${id}?start=0#fragment`, `dr-stream://user@play/${id}?start=0`,
  `dr-stream://play:80/${id}?start=0`, `dr-stream://play/../${id}?start=0`,
  `dr-stream://play/%2e%2e/${id}?start=0`, `dr-stream://play/${id}/?start=0`,
  `dr-stream://play/${id}?start=%31`, `dr-stream://play/${id}?start=${"9".repeat(310)}`,
  `dr-stream://play/${id}?start=0\n`, `dr-stream://play/${id}`,
  `dr-stream://play/${id}?start=0&revision=-1`, `dr-stream://play/${id}?start=0&revision=1.5`,
  `dr-stream://play/${id}?start=0&revision=2147483648`, `dr-stream://play/${id}?start=0&revision=1&revision=2`
])("rejects malformed stream form %s without backend contact", async (url) => {
  const requested = jest.fn();
  server.on("request", requested);
  expect(() => parseStreamUrl(url)).toThrow();
  const response = await createStreamHandler(baseUrl, "secret")({ url, method: "GET" });
  expect(response.status).toBe(400);
  expect(requested).not.toHaveBeenCalled();
});

test("streams authenticated local bytes before EOF and preserves safe headers", async () => {
  let observed;
  let upstream;
  server.on("request", (request, response) => {
    observed = { path: request.url, method: request.method, token: request.headers["x-dr-download-token"] };
    upstream = response;
    response.writeHead(200, { "Content-Type": "video/mp4", "X-Stream-Start": "12.375", "X-Secret": "hidden", "Cache-Control": "public" });
    response.write("first-frame");
  });
  const response = await createStreamHandler(baseUrl, "secret")(new Request(`dr-stream://play/${id}?start=12.375&revision=7`));
  expect(observed).toEqual({ path: `/playback/${id}/stream?start=12.375&revision=7`, method: "GET", token: "secret" });
  expect(response.headers.get("Content-Type")).toBe("video/mp4");
  expect(response.headers.get("Cache-Control")).toBe("no-store");
  expect(response.headers.get("X-Stream-Start")).toBe("12.375");
  expect(response.headers.get("X-Secret")).toBeNull();
  const reader = response.body.getReader();
  expect(Buffer.from((await reader.read()).value).toString()).toBe("first-frame");
  upstream.end("last-frame");
  expect(Buffer.from((await reader.read()).value).toString()).toBe("last-frame");
  expect((await reader.read()).done).toBe(true);
});

test("propagates media reader cancellation to the backend connection", async () => {
  let closed;
  const disconnected = new Promise((resolve) => { closed = resolve; });
  server.on("request", (_request, response) => {
    response.on("close", closed);
    response.writeHead(200, { "Content-Type": "video/mp4" });
    response.write("frame");
  });
  const response = await createStreamHandler(baseUrl, "secret")(new Request(`dr-stream://play/${id}?start=0`));
  const reader = response.body.getReader();
  await reader.read();
  await reader.cancel();
  await disconnected;
});

test("propagates request abortion to the active backend connection", async () => {
  let closed;
  const disconnected = new Promise((resolve) => { closed = resolve; });
  server.on("request", (_request, response) => {
    response.on("close", closed);
    response.write("frame");
  });
  const controller = new AbortController();
  const response = await createStreamHandler(baseUrl, "secret")(new Request(`dr-stream://play/${id}?start=0`, { signal: controller.signal }));
  const reader = response.body.getReader();
  await reader.read();
  controller.abort();
  await expect(reader.read()).rejects.toThrow();
  await disconnected;
});

test("preserves upstream error status and safe structured cause", async () => {
  server.on("request", (_request, response) => {
    response.writeHead(410, { "Content-Type": "application/json" });
    response.end('{"detail":{"code":"stream_expired","message":"Expired","recovery":"Reload"}}');
  });
  const response = await createStreamHandler(baseUrl, "secret")(new Request(`dr-stream://play/${id}?start=0`));
  expect(response.status).toBe(410);
  expect(await response.json()).toEqual({ detail: { code: "stream_expired", message: "Expired", recovery: "Reload" } });
});

test("refuses backend redirects without forwarding the token to another host", async () => {
  let contacts = 0;
  server.on("request", (_request, response) => {
    contacts += 1;
    response.writeHead(302, { Location: `${baseUrl}/secret-target` });
    response.end();
  });
  const response = await createStreamHandler(baseUrl, "secret")(new Request(`dr-stream://play/${id}?start=0`));
  expect(response.status).toBe(502);
  expect(contacts).toBe(1);
  expect(JSON.stringify(await response.json())).not.toContain(baseUrl);
});

test("refuses methods other than GET and remote backend addresses", async () => {
  expect(() => createStreamHandler("https://remote.test", "secret")).toThrow("backend");
  const response = await createStreamHandler(baseUrl, "secret")({ url: `dr-stream://play/${id}?start=0`, method: "POST" });
  expect(response.status).toBe(405);
});

test("packaged renderer allows only the private stream scheme for added media", () => {
  const html = fs.readFileSync(path.resolve(__dirname, "../../public/index.html"), "utf8");
  const policy = html.match(/Content-Security-Policy" content="([^"]+)"/)[1];
  expect(policy.split(";").map((directive) => directive.trim())).toContain("media-src 'self' dr-stream:");
  expect(policy.split(";").map((directive) => directive.trim())).toContain("connect-src 'none'");
  expect(require("../../package.json").build.files).toContain("stream-protocol.js");
});
