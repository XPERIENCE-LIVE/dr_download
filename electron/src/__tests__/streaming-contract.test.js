/** @jest-environment node */

const { buildApiRequest } = require("../../ipc-contract");

const id = "172f421c-70bf-4ec4-83a5-c242207eb9e0";
const itemId = "ec42d170-6e0c-4240-a2cb-af4aeec96cca";
const source = { url: "https://www.youtube.com/watch?v=test", cookie_source: "none" };

test.each([
  ["startPlayback", [source], { method: "POST", path: "/playback", body: source }],
  ["stopPlayback", [id], { method: "DELETE", path: `/playback/${id}` }],
  ["getPlayback", [id], { method: "GET", path: `/playback/${id}` }],
  ["listPlaylists", [], { method: "GET", path: "/playlists" }],
  ["createPlaylist", [{ name: "  Study  " }], { method: "POST", path: "/playlists", body: { name: "Study" } }],
  ["renamePlaylist", [id, { name: "  Work " }], { method: "PUT", path: `/playlists/${id}`, body: { name: "Work" } }],
  ["deletePlaylist", [id], { method: "DELETE", path: `/playlists/${id}` }],
  ["addPlaylistItem", [id, { url: "https://vimeo.com/123", title: "Clip", duration: 12.5 }],
    { method: "POST", path: `/playlists/${id}/items`, body: { url: "https://vimeo.com/123", title: "Clip", duration: 12.5 } }],
  ["removePlaylistItem", [id, itemId], { method: "DELETE", path: `/playlists/${id}/items/${itemId}` }],
  ["importPlaylist", [{ ...source, request_id: id }], { method: "POST", path: "/playlists/import", body: { ...source, request_id: id } }],
  ["cancelPlaylistImport", [id], { method: "DELETE", path: `/playlists/import/${id}` }]
])("routes the declared %s operation", (operation, args, expected) => {
  expect(buildApiRequest(operation, args)).toEqual(expected);
});

test.each(["abc", "../secret", "172f421c-70bf-4ec4-83a5-c242207eb9e0/other", "172f421c-70bf-4ec4-83a5-c242207eb9e0\n", null, 10])(
  "all playlist and playback paths reject a non-UUID %p", (invalid) => {
    for (const operation of ["stopPlayback", "getPlayback", "renamePlaylist", "deletePlaylist", "addPlaylistItem", "removePlaylistItem", "cancelPlaylistImport"]) {
      expect(() => buildApiRequest(operation, [invalid, { name: "Name", ...source }])).toThrow("identifier");
    }
    expect(() => buildApiRequest("removePlaylistItem", [id, invalid])).toThrow("identifier");
    expect(() => buildApiRequest("importPlaylist", [{ ...source, request_id: invalid }])).toThrow("identifier");
  }
);

test.each([
  "http://youtube.com/watch?v=a", "https://evil.test/youtube.com", "https://youtube.com.evil.test/a",
  "https://youtube.com@evil.test/a", "https://user:password@youtube.com/a", "file:///youtube.com/a",
  "https://youtube.com:444/a", "https://youtube.com:443/a", "https://youtu.be.evil.test/a", "https://vimeo.com\\@evil.test/a",
  "https://youtube.com/a\n", `https://youtube.com/${"a".repeat(2048)}`
])("rejects unsafe provider URL %p before contacting backend", (url) => {
  expect(() => buildApiRequest("startPlayback", [{ ...source, url }])).toThrow("URL");
  expect(() => buildApiRequest("addPlaylistItem", [id, { url }])).toThrow("URL");
  expect(() => buildApiRequest("importPlaylist", [{ ...source, request_id: id, url }])).toThrow("URL");
});

test.each(["https://youtube.com/watch?v=a", "https://m.youtube.com/watch?v=a", "https://youtu.be/a", "https://vimeo.com/123", "https://player.vimeo.com/video/123"])(
  "accepts supported provider URL %s", (url) => {
    expect(buildApiRequest("startPlayback", [{ ...source, url }]).body.url).toBe(url);
  }
);

test.each([true, "1080", 1080.5, 143, 2161, NaN, Infinity, null])("rejects invalid max_height %p", (max_height) => {
  expect(() => buildApiRequest("startPlayback", [{ ...source, max_height }])).toThrow("height");
});

test.each([144, 1080, 2160])("accepts strict max_height %p", (max_height) => {
  expect(buildApiRequest("startPlayback", [{ ...source, max_height }]).body.max_height).toBe(max_height);
});

test.each(["", "   ", "x".repeat(101), null, true])("rejects invalid playlist name %p", (name) => {
  expect(() => buildApiRequest("createPlaylist", [{ name }])).toThrow("name");
  expect(() => buildApiRequest("renamePlaylist", [id, { name }])).toThrow("name");
});

test.each(["chrome", true, 1, ""]) ("rejects invalid playback/import cookie source %p", (cookie_source) => {
  expect(() => buildApiRequest("startPlayback", [{ ...source, cookie_source }])).toThrow("cookie");
  expect(() => buildApiRequest("importPlaylist", [{ ...source, request_id: id, cookie_source }])).toThrow("cookie");
});

test.each([-1, Infinity, NaN, "12", true])("rejects invalid item duration %p", (duration) => {
  expect(() => buildApiRequest("addPlaylistItem", [id, { url: source.url, duration }])).toThrow("duration");
});

test("rejects undeclared payload fields and preserves the existing download contract", () => {
  expect(() => buildApiRequest("startPlayback", [{ ...source, headers: { Cookie: "secret" } }])).toThrow("request");
  expect(() => buildApiRequest("importPlaylist", [{ ...source, request_id: id, path: "C:/private" }])).toThrow("request");
  expect(buildApiRequest("getDownload", ["legacy-id"]).path).toBe("/downloads/legacy-id");
});
