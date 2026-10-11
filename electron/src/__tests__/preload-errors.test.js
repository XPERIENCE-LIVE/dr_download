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
