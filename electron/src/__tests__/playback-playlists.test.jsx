import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import Playback from "../components/Playback";
import Playlists from "../components/Playlists";
import { translator } from "../i18n";
import App from "../App";

const t = translator("en");
const first = { id: "one", url: "https://youtu.be/one", title: "First", available: true };
const second = { id: "two", url: "https://vimeo.com/123", title: "Second", available: true };
const metadata = (id = "session-one") => ({ session_id: id, title: id, duration: 90, height: 720, sponsor_segments: [], sponsor_status: "off" });
const config = { cookie_consent: false, sponsorblock_consent: false };

test("an old media error cannot stop the replacement stream after seeking", async () => {
  let finish;
  const api = apiMock({ getPlayback: jest.fn().mockImplementation(() => new Promise((resolve) => { finish = resolve; })) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first], index: 0 }} />);
  const slider = await screen.findByRole("slider", { name: "Position" });
  fireEvent.error(container.querySelector("video"));
  await waitFor(() => expect(api.getPlayback).toHaveBeenCalledTimes(1));
  fireEvent.change(slider, { target: { value: "15.23" } });
  await act(async () => finish({ error: { code: "stream_unavailable" } }));
  expect(api.stopPlayback).not.toHaveBeenCalled();
  expect(container.querySelector("video").getAttribute("src")).toContain("start=15.23");
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("a truncated stream is shown as failure instead of successful playlist advancement", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ error: { code: "network_error" } }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first, second], index: 0 }} />);
  await screen.findByText("session-one");
  fireEvent.ended(container.querySelector("video"));
  await waitFor(() => expect(api.stopPlayback).toHaveBeenCalledWith("session-one"));
  expect(api.startPlayback).toHaveBeenCalledTimes(1);
  expect(screen.queryByText("Ended")).not.toBeInTheDocument();
  expect(screen.getByRole("alert")).toBeInTheDocument();
});

test("provider denial before playback starts skips the unavailable playlist item with its cause", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ error: { code: "source_access_denied" } }),
    startPlayback: jest.fn().mockResolvedValueOnce(metadata()).mockResolvedValue(metadata("second-session")) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first, second], index: 0 }} />);
  await screen.findByText("session-one");
  fireEvent.error(container.querySelector("video"));
  await screen.findByText("second-session");
  expect(api.stopPlayback).toHaveBeenCalledWith("session-one");
  expect(screen.getByText(/First.*provider denied access/)).toBeInTheDocument();
});

test("provider denial after playback started remains visible without skipping the rest of the video", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ error: { code: "source_access_denied" } }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first, second], index: 0 }} />);
  await screen.findByText("session-one");
  fireEvent.playing(container.querySelector("video"));
  fireEvent.error(container.querySelector("video"));
  await waitFor(() => expect(api.stopPlayback).toHaveBeenCalledWith("session-one"));
  expect(api.startPlayback).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("alert")).toHaveTextContent(/provider denied access/);
});

test("initial provider denial while going Previous continues in the requested direction", async () => {
  const third = { ...second, url: "https://vimeo.com/456" };
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ error: { code: "source_access_denied" } }),
    startPlayback: jest.fn().mockResolvedValueOnce(metadata("third-session")).mockResolvedValueOnce(metadata("second-session")).mockResolvedValue(metadata("first-session")) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first, second, third], index: 2 }} />);
  await screen.findByText("third-session");
  fireEvent.click(screen.getByRole("button", { name: "Previous" }));
  await screen.findByText("second-session");
  fireEvent.error(container.querySelector("video"));
  await screen.findByText("first-session");
  expect(api.startPlayback.mock.calls.map(([body]) => body.url)).toEqual([third.url, second.url, first.url]);
});
test("an early end without a backend error cannot advance a playlist", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ status: "playing", error: null }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first, second], index: 0 }} />);
  await screen.findByText("session-one");
  Object.defineProperty(container.querySelector("video"), "currentTime", { configurable: true, value: 1 });
  fireEvent.ended(container.querySelector("video"));
  await waitFor(() => expect(api.stopPlayback).toHaveBeenCalledWith("session-one"));
  expect(api.startPlayback).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("alert")).toBeInTheDocument();
});
test("a backend-confirmed natural end tolerates provider duration rounded to whole seconds", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ status: "ended", error: null }),
    startPlayback: jest.fn().mockResolvedValueOnce(metadata()).mockResolvedValue(metadata("second-session")) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first, second], index: 0 }} />);
  await screen.findByText("session-one");
  Object.defineProperty(container.querySelector("video"), "currentTime", { configurable: true, value: 89.62 });
  fireEvent.ended(container.querySelector("video"));
  await screen.findByText("second-session");
  expect(api.startPlayback).toHaveBeenCalledTimes(2);
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
beforeEach(() => {
  jest.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  jest.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  Object.defineProperty(HTMLVideoElement.prototype, "requestVideoFrameCallback", { configurable: true, value: jest.fn() });
});
afterEach(() => { jest.restoreAllMocks(); });
function presentFrame(video, time) {
  Object.defineProperty(video, "currentTime", { configurable: true, value: time });
  const callback = video.requestVideoFrameCallback.mock.calls.at(-1)[0];
  act(() => callback(0, { mediaTime: time }));
}
function apiMock(overrides = {}) {
  return { startPlayback: jest.fn().mockResolvedValue(metadata()), stopPlayback: jest.fn().mockResolvedValue(null),
    listPlaylists: jest.fn().mockResolvedValue([{ id: "list", name: "My list", items: [first], created_at: "today" }]),
    createPlaylist: jest.fn().mockResolvedValue({ id: "new", name: "New", items: [] }), renamePlaylist: jest.fn().mockResolvedValue({}),
    deletePlaylist: jest.fn().mockResolvedValue(null), addPlaylistItem: jest.fn().mockResolvedValue({ ...first, duplicate: false }),
    removePlaylistItem: jest.fn().mockResolvedValue(null), importPlaylist: jest.fn(), cancelPlaylistImport: jest.fn().mockResolvedValue(null), ...overrides };
}

test("ordered playback skips unavailable/failing entries visibly and stops at the end", async () => {
  const api = apiMock({ startPlayback: jest.fn().mockRejectedValueOnce({ code: "stream_unavailable" }).mockResolvedValue(metadata("second-session")) });
  const items = [first, { id: "deleted", title: "Deleted video", available: false }, second];
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items, index: 0 }} />);
  await screen.findByText("second-session");
  expect(screen.getByText(/First.*No playable stream/)).toBeInTheDocument();
  expect(screen.getByText(/Deleted video.*unavailable/)).toBeInTheDocument();
  Object.defineProperty(container.querySelector("video"), "currentTime", { configurable: true, value: 90 });
  fireEvent.ended(container.querySelector("video"));
  await waitFor(() => expect(api.stopPlayback).toHaveBeenCalledWith("second-session"));
  expect(api.startPlayback).toHaveBeenCalledTimes(2);
  expect(screen.getByText("Ended")).toBeInTheDocument();
});

test("seeking uses finite decimals and displays the absolute position across restarts", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ ...metadata(), actual_start: 20.5 }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first], index: 0 }} />);
  const slider = await screen.findByRole("slider", { name: "Position" });
  fireEvent.change(slider, { target: { value: "20.5" } });
  const video = container.querySelector("video");
  expect(video.getAttribute("src")).toBe("dr-stream://play/session-one?start=20.5&revision=2");
  Object.defineProperty(video, "readyState", { configurable: true, value: 3 });
  await act(async () => fireEvent.loadedMetadata(video));
  Object.defineProperty(video, "currentTime", { configurable: true, value: 3 });
  fireEvent.timeUpdate(video);
  expect(slider).toHaveValue("23.5");
});

test("keyframe decoding slows near the seek target to avoid overshooting a paused position", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ ...metadata(), actual_start: 18 }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first], index: 0 }} />);
  fireEvent.change(await screen.findByRole("slider", { name: "Position" }), { target: { value: "20.5" } });
  const video = container.querySelector("video");
  Object.defineProperty(video, "readyState", { configurable: true, value: 3 });
  await act(async () => fireEvent.loadedMetadata(video));
  expect(video.playbackRate).toBe(4);
  presentFrame(video, 1);
  expect(video.playbackRate).toBe(4);
  presentFrame(video, 2.1);
  expect(video.playbackRate).toBe(1);
  expect(video).toHaveStyle({ visibility: "hidden" });
  presentFrame(video, 2.5);
  expect(video).toHaveStyle({ visibility: "visible" });
  expect(screen.getByRole("slider", { name: "Position" })).toHaveValue("20.5");
});

test("a late resolver is stopped after changing videos and on close", async () => {
  let finish;
  const api = apiMock({ startPlayback: jest.fn().mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; })).mockResolvedValue(metadata("new-session")) });
  const { rerender } = render(<Playback api={api} config={config} t={t} request={{ items: [first], index: 0 }} />);
  await waitFor(() => expect(api.startPlayback).toHaveBeenCalledTimes(1));
  rerender(<Playback api={api} config={config} t={t} request={{ items: [second], index: 0 }} />);
  await screen.findByText("new-session");
  await act(async () => finish(metadata("late-session")));
  expect(api.stopPlayback).toHaveBeenCalledWith("late-session");
  fireEvent.click(screen.getByRole("button", { name: "Close player" }));
  await waitFor(() => expect(api.stopPlayback).toHaveBeenCalledWith("new-session"));
});

test("a pending direct resolution disables duplicate Play while Close disposes the late session", async () => {
  let finish;
  const api = apiMock({ startPlayback: jest.fn().mockImplementation(() => new Promise((resolve) => { finish = resolve; })) });
  const { container } = render(<Playback api={api} config={config} t={t} />);
  fireEvent.change(screen.getByLabelText("Video link"), { target: { value: first.url } });
  fireEvent.click(screen.getByRole("button", { name: "Play" }));
  await waitFor(() => expect(api.startPlayback).toHaveBeenCalledTimes(1));
  expect(screen.getByRole("button", { name: "Play" })).toBeDisabled();
  fireEvent.submit(container.querySelector("form"));
  expect(api.startPlayback).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Close player" }));
  await act(async () => finish(metadata("late-session")));
  expect(api.stopPlayback).toHaveBeenCalledWith("late-session");
  expect(screen.getByRole("button", { name: "Play" })).toBeEnabled();
});

test("SponsorBlock skip has undo that permits watching the skipped segment", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValueOnce({ ...metadata(), actual_start: 15.75 }).mockResolvedValueOnce({ ...metadata(), actual_start: 10.25 }), startPlayback: jest.fn().mockResolvedValue({ ...metadata(), sponsor_status: "available", sponsor_segments: [{ start: 10.25, end: 15.75 }] }) });
  const { container } = render(<Playback api={api} config={{ ...config, sponsorblock_consent: true }} t={t} request={{ items: [first], index: 0 }} />);
  await screen.findByText("session-one");
  let video = container.querySelector("video");
  Object.defineProperty(video, "currentTime", { configurable: true, value: 11 });
  fireEvent.timeUpdate(video);
  expect(screen.getByText("Sponsor skipped")).toBeInTheDocument();
  expect(container.querySelector("video").getAttribute("src")).toContain("start=15.75");
  video = container.querySelector("video");
  Object.defineProperty(video, "readyState", { configurable: true, value: 3 });
  await act(async () => fireEvent.loadedMetadata(video));
  fireEvent.click(screen.getByRole("button", { name: "Undo skip" }));
  video = container.querySelector("video");
  expect(video.getAttribute("src")).toContain("start=10.25");
  Object.defineProperty(video, "readyState", { configurable: true, value: 3 });
  await act(async () => fireEvent.loadedMetadata(video));
  Object.defineProperty(video, "currentTime", { configurable: true, value: 1 });
  fireEvent.timeUpdate(video);
  expect(video.getAttribute("src")).toContain("start=10.25");
});

test("media failure offers reload and unknown duration has no seek slider", async () => {
  const api = apiMock({ startPlayback: jest.fn().mockResolvedValue({ ...metadata(), duration: null }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first], index: 0 }} />);
  await screen.findByText("session-one");
  expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  fireEvent.error(container.querySelector("video"));
  expect(screen.getByRole("alert")).toHaveTextContent("Reload");
  fireEvent.click(screen.getByRole("button", { name: "Reload" }));
  await waitFor(() => expect(api.startPlayback).toHaveBeenCalledTimes(2));
});

test("a successful SponsorBlock lookup without segments is visible", async () => {
  const api = apiMock({ startPlayback: jest.fn().mockResolvedValue({ ...metadata(), sponsor_status: "no_segments" }) });
  render(<Playback api={api} config={{ ...config, sponsorblock_consent: true }} t={t} request={{ items: [first], index: 0 }} />);
  expect(await screen.findByText("No promotional segments are registered for this video.")).toBeInTheDocument();
  expect(screen.queryByText("Sponsor skipped")).not.toBeInTheDocument();
});

test("playlist additions preserve metadata, warn about duplicates and play ordered items", async () => {
  const api = apiMock({ addPlaylistItem: jest.fn().mockResolvedValue({ ...first, duplicate: true }) });
  const onPlay = jest.fn();
  render(<Playlists api={api} config={config} t={t} pendingItem={first} onPlay={onPlay} />);
  await screen.findByRole("heading", { name: "My list" });
  fireEvent.click(screen.getByRole("button", { name: "Add to list" }));
  await waitFor(() => expect(api.addPlaylistItem).toHaveBeenCalledWith("list", { url: first.url, title: "First" }));
  expect(screen.getByText(/already in this list/)).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("button", { name: "Play list" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Play list" }));
  expect(onPlay).toHaveBeenCalledWith([first], 0);
});

test("playlist deletion requires explicit confirmation and failures remain visible", async () => {
  const api = apiMock({ deletePlaylist: jest.fn().mockRejectedValue({ code: "playlist_storage_error" }) });
  render(<Playlists api={api} config={config} t={t} onPlay={jest.fn()} />);
  await screen.findByRole("heading", { name: "My list" });
  fireEvent.click(screen.getByRole("button", { name: "Delete list" }));
  expect(api.deletePlaylist).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
  await waitFor(() => expect(api.deletePlaylist).toHaveBeenCalledWith("list"));
  expect(await screen.findByText("The local lists could not be saved or read.")).toBeInTheDocument();
});

test("import cancellation uses the same request UUID and ignores the late result", async () => {
  let finish;
  const api = apiMock({ importPlaylist: jest.fn().mockImplementation(() => new Promise((resolve) => { finish = resolve; })) });
  Object.defineProperty(window.crypto, "randomUUID", { configurable: true, value: jest.fn(() => "a116313b-8437-41b1-8c43-c35c29b06ccd") });
  render(<Playlists api={api} config={config} t={t} onPlay={jest.fn()} />);
  await screen.findByRole("heading", { name: "My list" });
  fireEvent.change(screen.getByLabelText("Playlist link"), { target: { value: "https://youtube.com/playlist?list=example" } });
  fireEvent.click(screen.getByRole("button", { name: "Import list" }));
  await waitFor(() => expect(api.importPlaylist).toHaveBeenCalled());
  const request = api.importPlaylist.mock.calls[0][0];
  expect(request.cookie_source).toBe("none");
  fireEvent.click(screen.getByRole("button", { name: "Cancel import" }));
  await waitFor(() => expect(api.cancelPlaylistImport).toHaveBeenCalledWith(request.request_id));
  await act(async () => finish({ playlist: { id: "ignored", name: "Late import", items: [] }, imported: 1, unavailable: 0 }));
  expect(screen.queryByText("Late import")).not.toBeInTheDocument();
});

test("a successful import stops being cancellable before the list refresh finishes", async () => {
  let finishImport;
  let finishRefresh;
  const imported = { id: "imported", name: "Imported", items: [first] };
  const api = apiMock({ importPlaylist: jest.fn().mockImplementation(() => new Promise((resolve) => { finishImport = resolve; })),
    listPlaylists: jest.fn().mockResolvedValueOnce([]).mockImplementationOnce(() => new Promise((resolve) => { finishRefresh = resolve; })) });
  render(<Playlists api={api} config={config} t={t} onPlay={jest.fn()} />);
  await screen.findByText("Create a list or import a YouTube or Vimeo playlist link.");
  fireEvent.change(screen.getByLabelText("Playlist link"), { target: { value: "https://youtube.com/playlist?list=example" } });
  fireEvent.click(screen.getByRole("button", { name: "Import list" }));
  await waitFor(() => expect(api.importPlaylist).toHaveBeenCalled());
  expect(screen.getByRole("button", { name: "Cancel import" })).toBeInTheDocument();
  await act(async () => finishImport({ playlist: imported, imported: 1, unavailable: 0 }));
  expect(screen.queryByRole("button", { name: "Cancel import" })).not.toBeInTheDocument();
  await act(async () => finishRefresh([imported]));
  expect(screen.getByRole("heading", { name: "Imported" })).toBeInTheDocument();
  expect(screen.getByText("Imported entries: 1 · Unavailable: 0")).toBeInTheDocument();
  expect(api.cancelPlaylistImport).not.toHaveBeenCalled();
});

test("cancel after backend commit refreshes the completed import without claiming cancellation", async () => {
  let finishImport;
  const imported = { id: "imported", name: "Imported", items: [first] };
  const api = apiMock({ importPlaylist: jest.fn().mockImplementation(() => new Promise((resolve) => { finishImport = resolve; })),
    cancelPlaylistImport: jest.fn().mockRejectedValue({ detail: { code: "playlist_import_completed" } }),
    listPlaylists: jest.fn().mockResolvedValueOnce([]).mockResolvedValue([imported]) });
  render(<Playlists api={api} config={config} t={t} onPlay={jest.fn()} />);
  await screen.findByText("Create a list or import a YouTube or Vimeo playlist link.");
  fireEvent.change(screen.getByLabelText("Playlist link"), { target: { value: "https://youtube.com/playlist?list=example" } });
  fireEvent.click(screen.getByRole("button", { name: "Import list" }));
  await waitFor(() => expect(api.importPlaylist).toHaveBeenCalled());
  fireEvent.click(screen.getByRole("button", { name: "Cancel import" }));
  expect(await screen.findByText("The import finished before cancellation. Your list is available.")).toBeInTheDocument();
  expect(screen.queryByText("Import cancelled")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Cancel import" })).not.toBeInTheDocument();
  await act(async () => finishImport({ playlist: imported, imported: 1, unavailable: 0 }));
  expect(screen.getByRole("heading", { name: "Imported" })).toBeInTheDocument();
});

test("loadedmetadata confirms actual keyframe offset; later time updates keep absolute time", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ ...metadata(), actual_start: 18.75 }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first], index: 0 }} />);
  const slider = await screen.findByRole("slider", { name: "Position" });
  fireEvent.change(slider, { target: { value: "20.5" } });
  const video = container.querySelector("video");
  fireEvent.loadedMetadata(video);
  await waitFor(() => expect(slider).toHaveValue("18.75"));
  Object.defineProperty(video, "readyState", { configurable: true, value: 3 });
  fireEvent.canPlay(video);
  presentFrame(video, 1.75);
  Object.defineProperty(video, "currentTime", { configurable: true, value: 4 });
  fireEvent.timeUpdate(video);
  expect(slider).toHaveValue("22.75");
});

test("seek discards the decoded keyframe lead-in before resuming at the requested decimal", async () => {
  const play = jest.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ ...metadata(), actual_start: 14 }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first], index: 0 }} />);
  const slider = await screen.findByRole("slider", { name: "Position" });
  fireEvent.change(slider, { target: { value: "15.23" } });
  const video = container.querySelector("video");
  expect(video.autoplay).toBe(false);
  fireEvent.loadedMetadata(video);
  await waitFor(() => expect(api.getPlayback).toHaveBeenCalled());
  expect(video.currentTime).toBe(0);
  Object.defineProperty(video, "readyState", { configurable: true, value: 3 });
  fireEvent.canPlay(video);
  expect(video.currentTime).toBe(0);
  expect(video.muted).toBe(true);
  presentFrame(video, 1.23);
  expect(video.currentTime).toBeCloseTo(1.23);
  expect(slider).toHaveValue("15.23");
  expect(play).toHaveBeenCalledTimes(1);
  play.mockRestore();
});

test("decimal seek discards hidden muted frames without a native byte seek and preserves pause", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ ...metadata(), actual_start: 20.13 }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first], index: 0 }} />);
  const slider = await screen.findByRole("slider", { name: "Position" });
  fireEvent.pause(container.querySelector("video"));
  fireEvent.change(slider, { target: { value: "20.5" } });
  const video = container.querySelector("video");
  Object.defineProperty(video, "currentTime", { configurable: true, get: () => 0, set: () => { throw new Error("Native byte seek unsupported"); } });
  Object.defineProperty(video, "readyState", { configurable: true, value: 3 });
  await act(async () => fireEvent.loadedMetadata(video));
  expect(screen.getByRole("button", { name: "Resume" })).toBeDisabled();
  expect(video).not.toBeVisible();
  expect(video.muted).toBe(true);
  presentFrame(video, 0.2);
  expect(screen.getByRole("button", { name: "Resume" })).toBeDisabled();
  presentFrame(video, 0.37);
  expect(video).toBeVisible();
  expect(video.muted).toBe(false);
  expect(slider).toHaveValue("20.5");
  expect(screen.getByRole("button", { name: "Resume" })).toBeEnabled();
  expect(screen.getByText("Paused")).toBeInTheDocument();
  expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled();
});

test("seeking while paused keeps playback paused and restores the Resume control", async () => {
  const api = apiMock({ getPlayback: jest.fn().mockResolvedValue({ ...metadata(), actual_start: 15.23 }) });
  const { container } = render(<Playback api={api} config={config} t={t} request={{ items: [first], index: 0 }} />);
  const slider = await screen.findByRole("slider", { name: "Position" });
  fireEvent.pause(container.querySelector("video"));
  fireEvent.change(slider, { target: { value: "15.23" } });
  const video = container.querySelector("video");
  expect(screen.getByRole("button", { name: "Resume" })).toBeDisabled();
  Object.defineProperty(video, "readyState", { configurable: true, value: 3 });
  await act(async () => fireEvent.loadedMetadata(video));
  expect(screen.getByRole("button", { name: "Resume" })).toBeEnabled();
  expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled();
  expect(screen.getByText("Paused")).toBeInTheDocument();
});

test("Previous and Next release the old session and keep the playlist order", async () => {
  const api = apiMock({ startPlayback: jest.fn().mockResolvedValueOnce(metadata("first-session")).mockResolvedValueOnce(metadata("second-session")).mockResolvedValueOnce(metadata("first-again")) });
  render(<Playback api={api} config={config} t={t} request={{ items: [first, second], index: 0 }} />);
  await screen.findByText("first-session");
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("second-session");
  expect(api.stopPlayback).toHaveBeenCalledWith("first-session");
  fireEvent.click(screen.getByRole("button", { name: "Previous" }));
  await screen.findByText("first-again");
  expect(api.stopPlayback).toHaveBeenCalledWith("second-session");
  expect(api.startPlayback.mock.calls.map(([body]) => body.url)).toEqual([first.url, second.url, first.url]);
});

test("SponsorBlock permission is enabled only after a successful persisted confirmation", async () => {
  let confirm;
  const api = apiMock({ getConfig: jest.fn().mockResolvedValue({ ...config, language: "en", cookie_source: "none" }), listDownloads: jest.fn().mockResolvedValue([]),
    updateConfig: jest.fn().mockImplementationOnce(() => Promise.reject({ code: "engine_unavailable" })).mockImplementationOnce(() => new Promise((resolve) => { confirm = resolve; })) });
  window.drDownload = api;
  render(<App />);
  await screen.findByText("LOCAL ENGINE READY");
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(screen.getByRole("button", { name: "Allow SponsorBlock and save" }));
  await screen.findByText("The playback engine is unavailable.");
  expect(screen.queryByRole("button", { name: "Revoke SponsorBlock and save" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Allow SponsorBlock and save" }));
  expect(screen.queryByRole("button", { name: "Revoke SponsorBlock and save" })).not.toBeInTheDocument();
  await act(async () => confirm({ status: "ok" }));
  expect(screen.getByRole("button", { name: "Revoke SponsorBlock and save" })).toBeInTheDocument();
});

test("playing a direct link survives navigation and stops when the app unmounts", async () => {
  const api = apiMock({ getConfig: jest.fn().mockResolvedValue({ ...config, language: "en", cookie_source: "none" }), listDownloads: jest.fn().mockResolvedValue([]) });
  window.drDownload = api;
  const { container, unmount } = render(<App />);
  await screen.findByText("LOCAL ENGINE READY");
  fireEvent.click(screen.getByRole("button", { name: "Player" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Video link" }), { target: { value: first.url } });
  fireEvent.click(screen.getByRole("button", { name: "Play" }));
  await screen.findByText("session-one");
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(container.querySelector("video")).toBeInTheDocument();
  expect(api.stopPlayback).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Player" }));
  expect(screen.getByText("session-one")).toBeVisible();
  unmount();
  expect(api.stopPlayback).toHaveBeenCalledWith("session-one");
});

test("create, rename and remove operations refresh persistent list state", async () => {
  const initial = { id: "list", name: "My list", items: [first] };
  const created = { id: "new", name: "New", items: [] };
  const renamed = { ...created, name: "Renamed", items: [second] };
  const api = apiMock({ listPlaylists: jest.fn().mockResolvedValueOnce([initial]).mockResolvedValueOnce([initial, created]).mockResolvedValueOnce([initial, renamed]).mockResolvedValue([initial, { ...renamed, items: [] }]) });
  render(<Playlists api={api} config={config} t={t} onPlay={jest.fn()} />);
  await screen.findByRole("heading", { name: "My list" });
  fireEvent.change(screen.getByLabelText("New list name"), { target: { value: "New" } });
  fireEvent.click(screen.getByRole("button", { name: "Create list" }));
  await screen.findByRole("heading", { name: "New" });
  await waitFor(() => expect(screen.getByLabelText("List name")).toBeEnabled());
  fireEvent.change(screen.getByLabelText("List name"), { target: { value: "Renamed" } });
  fireEvent.click(screen.getByRole("button", { name: "Save name" }));
  await screen.findByRole("heading", { name: "Renamed" });
  expect(api.renamePlaylist).toHaveBeenCalledWith("new", { name: "Renamed" });
  await waitFor(() => expect(screen.getByRole("button", { name: "Remove: Second" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Remove: Second" }));
  await screen.findByText("Add a link to get started.");
  expect(api.removePlaylistItem).toHaveBeenCalledWith("new", "two");
});
