/** @jest-environment node */

const http = require("http");
const { requestBackend } = require("../../backend-client");

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

test("reads the authenticated history from the real local HTTP server", async () => {
  let observed;
  server.on("request", (request, response) => {
    observed = { url: request.url, method: request.method, token: request.headers["x-dr-download-token"] };
    response.setHeader("Content-Type", "application/json");
    response.end('[{"id":"one","status":"completed"}]');
  });
  await expect(requestBackend(baseUrl, "session-token", "listDownloads", [])).resolves.toEqual([
    { id: "one", status: "completed" }
  ]);
  expect(observed).toEqual({ url: "/downloads", method: "GET", token: "session-token" });
});

test("aborts a stalled history body and permits a subsequent read", async () => {
  let reads = 0;
  server.on("request", (_request, response) => {
    reads += 1;
    response.setHeader("Content-Type", "application/json");
    if (reads === 1) response.write("[");
    else response.end("[]");
  });
  await expect(requestBackend(baseUrl, "session-token", "listDownloads", [])).rejects.toThrow();
  await expect(requestBackend(baseUrl, "session-token", "listDownloads", [])).resolves.toEqual([]);
}, 15000);

test("preserves structured backend errors and their recovery advice", async () => {
  server.on("request", (_request, response) => {
    response.writeHead(409, { "Content-Type": "application/json" });
    response.end('{"detail":{"code":"busy","message":"Motor ocupado.","recovery":"Reintenta."}}');
  });
  await expect(requestBackend(baseUrl, "session-token", "listDownloads", [])).rejects.toMatchObject({
    message: "Motor ocupado. Reintenta.",
    detail: { code: "busy", message: "Motor ocupado.", recovery: "Reintenta." }
  });
});
