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

const downloadBody = (body) => {
  requestBody(body);
  if (typeof body.format_id !== "string" || !/^[A-Za-z0-9_.:-]{1,128}$/.test(body.format_id)) {
    throw new Error("Invalid format identifier");
  }
  if (body.estimated_bytes != null &&
      (!Number.isSafeInteger(body.estimated_bytes) || body.estimated_bytes < 0)) {
    throw new Error("Invalid size estimate");
  }
  return body;
};

const uuidPath = (id) => {
  if (typeof id !== "string" || id.length !== 36 || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    throw new Error("Invalid identifier");
  }
  return id;
};

const boundedBody = (body, keys) => {
  if (!body || typeof body !== "object" || Array.isArray(body) || Object.keys(body).some((key) => !keys.includes(key))) {
    throw new Error("Invalid request");
  }
  return body;
};

const providerUrl = (url) => {
  if (typeof url !== "string" || url.length < 8 || url.length > 2048 || /[\s\\]/.test(url)) {
    throw new Error("Invalid provider URL");
  }
  let parsed;
  try { parsed = new URL(url); } catch { throw new Error("Invalid provider URL"); }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.port || /^https:\/\/[^/?#]*:/i.test(url) ||
      !["youtube.com", "youtu.be", "vimeo.com"].some((host) => parsed.hostname === host || parsed.hostname.endsWith(`.${host}`))) {
    throw new Error("Invalid provider URL");
  }
  return url;
};

const sourceBody = (body, keys) => {
  boundedBody(body, keys);
  providerUrl(body.url);
  if (body.cookie_source !== undefined && !["none", "edge", "firefox"].includes(body.cookie_source)) {
    throw new Error("Invalid cookie source");
  }
  return body;
};

const playbackBody = (body) => {
  sourceBody(body, ["url", "cookie_source", "max_height"]);
  if (body.max_height !== undefined && (!Number.isInteger(body.max_height) || body.max_height < 144 || body.max_height > 2160)) {
    throw new Error("Invalid playback height");
  }
  return body;
};

const playlistNameBody = (body) => {
  boundedBody(body, ["name"]);
  if (typeof body.name !== "string" || !body.name.trim() || Array.from(body.name.trim()).length > 100) {
    throw new Error("Invalid playlist name");
  }
  return { name: body.name.trim() };
};

const playlistItemBody = (body) => {
  boundedBody(body, ["url", "title", "duration", "thumbnail"]);
  providerUrl(body.url);
  if (body.duration != null && (typeof body.duration !== "number" || !Number.isFinite(body.duration) || body.duration < 0)) {
    throw new Error("Invalid item duration");
  }
  if (body.title != null && (typeof body.title !== "string" || body.title.length > 500)) throw new Error("Invalid item title");
  if (body.thumbnail != null && (typeof body.thumbnail !== "string" || body.thumbnail.length > 2048 || !/^https:\/\//.test(body.thumbnail))) {
    throw new Error("Invalid item thumbnail");
  }
  return body;
};

const playlistImportBody = (body) => {
  sourceBody(body, ["request_id", "url", "cookie_source"]);
  uuidPath(body.request_id);
  return body;
};

const routes = {
  inspectMedia: ([body]) => ({ method: "POST", path: "/media/inspect", body: requestBody(body) }),
  createDownload: ([body]) => ({ method: "POST", path: "/downloads", body: downloadBody(body) }),
  listDownloads: () => ({ method: "GET", path: "/downloads" }),
  getDownload: ([id]) => ({ method: "GET", path: `/downloads/${taskPath(id)}` }),
  cancelDownload: ([id]) => ({ method: "POST", path: `/downloads/${taskPath(id)}/cancel` }),
  retryDownload: ([id]) => ({ method: "POST", path: `/downloads/${taskPath(id)}/retry` }),
  deleteDownload: ([id]) => ({ method: "DELETE", path: `/downloads/${taskPath(id)}` }),
  getConfig: () => ({ method: "GET", path: "/config/" }),
  updateConfig: ([body]) => ({ method: "PUT", path: "/config", body }),
  validateDirectory: ([body]) => ({ method: "POST", path: "/directories/validate", body: directoryBody(body) }),
  startPlayback: ([body]) => ({ method: "POST", path: "/playback", body: playbackBody(body) }),
  stopPlayback: ([id]) => ({ method: "DELETE", path: `/playback/${uuidPath(id)}` }),
  getPlayback: ([id]) => ({ method: "GET", path: `/playback/${uuidPath(id)}` }),
  listPlaylists: () => ({ method: "GET", path: "/playlists" }),
  createPlaylist: ([body]) => ({ method: "POST", path: "/playlists", body: playlistNameBody(body) }),
  renamePlaylist: ([id, body]) => ({ method: "PUT", path: `/playlists/${uuidPath(id)}`, body: playlistNameBody(body) }),
  deletePlaylist: ([id]) => ({ method: "DELETE", path: `/playlists/${uuidPath(id)}` }),
  addPlaylistItem: ([id, body]) => ({ method: "POST", path: `/playlists/${uuidPath(id)}/items`, body: playlistItemBody(body) }),
  removePlaylistItem: ([id, itemId]) => ({ method: "DELETE", path: `/playlists/${uuidPath(id)}/items/${uuidPath(itemId)}` }),
  importPlaylist: ([body]) => ({ method: "POST", path: "/playlists/import", body: playlistImportBody(body) }),
  cancelPlaylistImport: ([requestId]) => ({ method: "DELETE", path: `/playlists/import/${uuidPath(requestId)}` })
};

function buildApiRequest(operation, args = []) {
  if (!Object.prototype.hasOwnProperty.call(routes, operation)) {
    throw new Error("Unsupported operation");
  }
  return routes[operation](args);
}

module.exports = { buildApiRequest };
