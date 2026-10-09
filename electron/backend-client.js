const { buildApiRequest } = require("./ipc-contract");

async function waitForBackend(baseUrl, sessionToken, child) {
  let lastError;
  // First startup downloads and verifies the engine before health is available.
  const deadline = Date.now() + 120000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) throw new Error("Backend exited before becoming ready");
    try {
      const response = await fetch(`${baseUrl}/health`, {
        headers: { "X-Dr-Download-Token": sessionToken },
        signal: AbortSignal.timeout(Math.min(2000, deadline - Date.now()))
      });
      if (response.ok) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Backend did not start in time${lastError ? `: ${lastError.name}` : ""}`);
}

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

module.exports = { requestBackend, waitForBackend };
