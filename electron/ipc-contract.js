const taskPath = (id) => {
  if (typeof id !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(id)) {
    throw new Error("Invalid task identifier");
  }
  return encodeURIComponent(id);
};

const requestBody = (body) => {
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error("Invalid request");
  if (typeof body.url !== "string" || body.url.length < 8 || body.url.length > 2048) {
    throw new Error("Invalid URL");
  }
  if (body.cookie_source && !["none", "edge", "firefox"].includes(body.cookie_source)) {
    throw new Error("Invalid cookie source");
  }
  return body;
};

const directoryBody = (body) => {
  if (!body || typeof body !== "object" || Array.isArray(body) || typeof body.path !== "string") {
    throw new Error("Invalid directory request");
  }
  return { path: body.path };
};

const routes = {
  inspectMedia: ([body]) => ({ method: "POST", path: "/media/inspect", body: requestBody(body) }),
  createDownload: ([body]) => ({ method: "POST", path: "/downloads", body: requestBody(body) }),
  listDownloads: () => ({ method: "GET", path: "/downloads" }),
  getDownload: ([id]) => ({ method: "GET", path: `/downloads/${taskPath(id)}` }),
  cancelDownload: ([id]) => ({ method: "POST", path: `/downloads/${taskPath(id)}/cancel` }),
  retryDownload: ([id]) => ({ method: "POST", path: `/downloads/${taskPath(id)}/retry` }),
  deleteDownload: ([id]) => ({ method: "DELETE", path: `/downloads/${taskPath(id)}` }),
  getConfig: () => ({ method: "GET", path: "/config/" }),
  updateConfig: ([body]) => ({ method: "PUT", path: "/config", body }),
  validateDirectory: ([body]) => ({ method: "POST", path: "/directories/validate", body: directoryBody(body) })
};

function buildApiRequest(operation, args = []) {
  if (!Object.prototype.hasOwnProperty.call(routes, operation)) {
    throw new Error("Unsupported operation");
  }
  return routes[operation](args);
}

module.exports = { buildApiRequest };
