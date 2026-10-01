const { buildApiRequest } = require("./ipc-contract");

async function requestBackend(baseUrl, sessionToken, operation, args) {
  const request = buildApiRequest(operation, args);
  const response = await fetch(`${baseUrl}${request.path}`, {
    method: request.method,
    headers: {
      "Content-Type": "application/json",
      "X-Dr-Download-Token": sessionToken
    },
    body: request.body === undefined ? undefined : JSON.stringify(request.body),
    // Bound the entire history response, including a body that stops arriving.
    signal: operation === "listDownloads" ? AbortSignal.timeout(10000) : undefined
  });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.message || payload?.detail || `HTTP ${response.status}`;
    const recovery = payload?.detail?.recovery;
    const error = new Error(recovery ? `${message} ${recovery}` : message);
    error.detail = payload?.detail;
    throw error;
  }
  return payload;
}

module.exports = { requestBackend };
