/** @jest-environment node */
jest.mock("electron", () => ({ contextBridge: { exposeInMainWorld: jest.fn() }, ipcRenderer: { invoke: jest.fn() } }), { virtual: true });
const { contextBridge, ipcRenderer } = require("electron");
require("../../preload");
const api = contextBridge.exposeInMainWorld.mock.calls[0][1];

test("preserves structured backend failures across the serialized IPC boundary", async () => {
  const detail = { code: "format_unavailable", message: "No disponible", recovery: "Elige otro formato" };
  ipcRenderer.invoke.mockResolvedValue(globalThis.structuredClone({ drDownloadError: detail }));
  await expect(api.inspectMedia({ url: "https://example.com/video" })).rejects.toMatchObject({ detail });
});

test("returns successful IPC payloads unchanged", async () => {
  const payload = { title: "Video", formats: [] };
  ipcRenderer.invoke.mockResolvedValue(payload);
  await expect(api.inspectMedia({ url: "https://example.com/video" })).resolves.toEqual(payload);
});

test.each([
  ["startPlayback", [{ url: "https://youtube.com/watch?v=a", cookie_source: "none" }]],
  ["stopPlayback", ["session-id"]], ["getPlayback", ["session-id"]], ["listPlaylists", []], ["createPlaylist", [{ name: "List" }]],
  ["renamePlaylist", ["list-id", { name: "Renamed" }]], ["deletePlaylist", ["list-id"]],
  ["addPlaylistItem", ["list-id", { url: "https://vimeo.com/123" }]],
  ["removePlaylistItem", ["list-id", "item-id"]],
  ["importPlaylist", [{ url: "https://youtube.com/playlist?list=a", cookie_source: "none", request_id: "request-id" }]],
  ["cancelPlaylistImport", ["request-id"]]
])("exposes %s through the existing enumerated bridge", async (method, args) => {
  ipcRenderer.invoke.mockResolvedValue({ ok: true });
  await expect(api[method](...args)).resolves.toEqual({ ok: true });
  expect(ipcRenderer.invoke).toHaveBeenLastCalledWith("dr-download:api", method, ...args);
});
