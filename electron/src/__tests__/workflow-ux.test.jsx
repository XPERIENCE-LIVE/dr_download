import React from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "../App";

const media = {
  title: "Mi vídeo", author: "Autor", duration: 90,
  formats: [
    { id: "video-compatible", kind: "video", preset: true, label: "Vídeo compatible", container: "mp4", estimated_bytes: 1000000 },
    { id: "video-best", kind: "video", preset: true, label: "Máxima calidad", container: "mp4", estimated_bytes: null },
    { id: "audio-mp3", kind: "audio", preset: true, label: "MP3", container: "mp3", estimated_bytes: 500000 },
    { id: "audio-original", kind: "audio", preset: true, label: "Audio original" },
    { id: "137", kind: "video", label: "1080p", estimated_bytes: 900000 }
  ]
};

function installApi(overrides = {}) {
  window.drDownload = {
    getConfig: jest.fn().mockResolvedValue({ language: "es", cookie_source: "none", cookie_consent: false,
      notifications: false, output_dir: "C:\\Downloads", default_format: "video" }),
    listDownloads: jest.fn().mockResolvedValue([]),
    inspectMedia: jest.fn().mockResolvedValue(media),
    validateDirectory: jest.fn().mockResolvedValue({ accepted: true, path: "C:\\Downloads", free_bytes: 500000000 }),
    createDownload: jest.fn().mockResolvedValue({ id: "new", status: "queued", url: "https://example.com/video" }),
    selectFolder: jest.fn(), updateConfig: jest.fn().mockResolvedValue({ status: "ok" }),
    retryDownload: jest.fn(), cancelDownload: jest.fn(), deleteDownload: jest.fn(),
    openDownload: jest.fn(), exportDiagnostics: jest.fn().mockResolvedValue(true), notify: jest.fn(),
    ...overrides
  };
}

async function inspect() {
  await screen.findByText("MOTOR LOCAL LISTO");
  fireEvent.change(screen.getByLabelText("Enlace del video"), { target: { value: "https://example.com/video" } });
  fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));
  await screen.findByText("Mi vídeo");
}

beforeEach(() => installApi());

test("does not announce a ready engine before a successful read or after a failed read", async () => {
  let rejectRead;
  installApi({ listDownloads: jest.fn(() => new Promise((resolve, reject) => { rejectRead = reject; })) });
  render(<App />);
  expect(screen.queryByText("MOTOR LOCAL LISTO")).not.toBeInTheDocument();
  expect(screen.getByText("CONECTANDO…")).toBeInTheDocument();
  await act(async () => rejectRead(new Error("Backend sin conexión")));
  expect(screen.getByText("MOTOR NO DISPONIBLE")).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("Backend sin conexión");
});

test("inspection shows indeterminate progress without inventing a percentage", async () => {
  installApi({ inspectMedia: jest.fn(() => new Promise(() => {})) });
  render(<App />);
  await screen.findByText("MOTOR LOCAL LISTO");
  fireEvent.change(screen.getByLabelText("Enlace del video"), { target: { value: "https://example.com/video" } });
  fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));
  expect(screen.getByRole("progressbar")).not.toHaveAttribute("aria-valuenow");
  expect(screen.queryByLabelText("42%")).not.toBeInTheDocument();
});

test("transfer strip prefers a running download over an earlier queued entry", async () => {
  installApi({ listDownloads: jest.fn().mockResolvedValue([
    { id: "waiting", title: "Esperando", status: "queued" },
    { id: "running", title: "En ejecución", status: "downloading", progress: 12 }
  ]) });
  render(<App />);
  expect(await screen.findByText("En ejecución")).toBeInTheDocument();
  expect(screen.queryByText("Esperando")).not.toBeInTheDocument();
});

test("keeps the inspected draft and selected format when navigating to settings", async () => {
  render(<App />);
  await inspect();
  fireEvent.change(screen.getByLabelText("Formato y calidad"), { target: { value: "audio-mp3" } });
  fireEvent.click(screen.getByRole("button", { name: "Ajustes" }));
  fireEvent.click(screen.getByRole("button", { name: "Nueva descarga" }));
  expect(screen.getByLabelText("Enlace del video")).toHaveValue("https://example.com/video");
  expect(screen.getByText("Mi vídeo")).toBeVisible();
  expect(screen.getByLabelText("Formato y calidad")).toHaveValue("audio-mp3");
});

test("inspection errors show recovery and allow another inspection", async () => {
  installApi({ inspectMedia: jest.fn().mockRejectedValueOnce({ detail: {
    message: "No se pudo analizar", recovery: "Comprueba este enlace y vuelve a analizarlo."
  } }).mockResolvedValue(media) });
  render(<App />);
  await screen.findByText("MOTOR LOCAL LISTO");
  fireEvent.change(screen.getByLabelText("Enlace del video"), { target: { value: "https://example.com/video" } });
  fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Comprueba este enlace y vuelve a analizarlo.");
  fireEvent.click(screen.getByRole("button", { name: "Volver a analizar" }));
  expect(await screen.findByText("Mi vídeo")).toBeInTheDocument();
});

test("queueing has its own pending phase and offers a direct route to the queue", async () => {
  let resolveQueue;
  installApi({ createDownload: jest.fn(() => new Promise((resolve) => { resolveQueue = resolve; })) });
  render(<App />);
  await inspect();
  fireEvent.click(screen.getByRole("button", { name: "Agregar a la cola" }));
  expect(screen.getByRole("button", { name: "Agregando…" })).toBeDisabled();
  expect(screen.queryByRole("button", { name: "Analizando…" })).not.toBeInTheDocument();
  await waitFor(() => expect(typeof resolveQueue).toBe("function"));
  await act(async () => resolveQueue({ id: "new", status: "queued", title: "Mi tarea" }));
  fireEvent.click(screen.getByRole("button", { name: "Ver cola" }));
  expect(screen.getByRole("heading", { name: "Cola" })).toBeInTheDocument();
});

test("shows simple presets and size while keeping stream selection advanced", async () => {
  render(<App />);
  await inspect();
  const select = screen.getByLabelText("Formato y calidad");
  expect(within(select).getAllByRole("option")).toHaveLength(3);
  expect(select).toHaveValue("video-compatible");
  expect(screen.getByText(/Tamaño aproximado.*977 KB/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("checkbox", { name: "Formatos avanzados" }));
  expect(within(select).getByRole("option", { name: /1080p/ })).toBeInTheDocument();
  fireEvent.change(select, { target: { value: "video-best" } });
  expect(screen.getByText(/Tamaño aproximado desconocido/)).toBeInTheDocument();
    expect(screen.getByText(/reproductor compatible/)).toBeInTheDocument();
});

test("blocks queueing when the known estimate exceeds available processing space", async () => {
  installApi({ validateDirectory: jest.fn().mockResolvedValue({ accepted: true, path: "C:\\Downloads", free_bytes: 150000000 }),
    inspectMedia: jest.fn().mockResolvedValue({ ...media, formats: [{ ...media.formats[0], estimated_bytes: 100000000 }] }) });
  render(<App />);
  await inspect();
  expect(screen.getByRole("button", { name: "Agregar a la cola" })).toBeDisabled();
  expect(screen.getByRole("alert")).toHaveTextContent("espacio");
});

test("history search and state filter narrow the displayed downloads", async () => {
  installApi({ listDownloads: jest.fn().mockResolvedValue([
    { id: "one", title: "Concierto", status: "completed", filename: "C:\\audio.mp3" },
    { id: "two", title: "Entrevista", status: "failed" }
  ]) });
  render(<App />);
  await screen.findByText("MOTOR LOCAL LISTO");
  fireEvent.click(screen.getByRole("button", { name: "Historial" }));
  fireEvent.change(screen.getByLabelText("Buscar en el historial"), { target: { value: "audio.mp3" } });
  expect(screen.getByText("Concierto")).toBeInTheDocument();
  expect(screen.queryByText("Entrevista")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Buscar en el historial"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("Estado"), { target: { value: "failed" } });
  expect(screen.getByText("Entrevista")).toBeInTheDocument();
  expect(screen.queryByText("Concierto")).not.toBeInTheDocument();
});

test("warns about a repeated link while allowing an intentional new copy", async () => {
  installApi({ listDownloads: jest.fn().mockResolvedValue([{ id: "old", status: "completed", url: "https://example.com/video" }]) });
  render(<App />);
  await inspect();
  expect(screen.getByText(/Este enlace ya aparece/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Agregar a la cola" }));
  expect(await screen.findByRole("button", { name: "Ver cola" })).toBeInTheDocument();
});

test("settings display a failed save and confirm a successful retry", async () => {
  installApi({ updateConfig: jest.fn().mockRejectedValueOnce(new Error("No se guardó la configuración")).mockResolvedValue({ status: "ok" }) });
  render(<App />);
  await screen.findByText("MOTOR LOCAL LISTO");
  fireEvent.click(screen.getByRole("button", { name: "Ajustes" }));
  fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("No se guardó la configuración");
  fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
  expect(await screen.findByText("Cambios guardados")).toBeInTheDocument();
});

test("failed consent persistence keeps browser access unauthorized", async () => {
  installApi({ getConfig: jest.fn().mockResolvedValue({ language: "es", cookie_source: "edge", cookie_consent: false,
    output_dir: "C:\\Downloads", default_format: "video" }),
  updateConfig: jest.fn().mockRejectedValue(new Error("No se pudo guardar la autorización")) });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Autorizar uso" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo guardar la autorización");
  expect(screen.getByRole("button", { name: "Autorizar uso" })).toBeInTheDocument();
  await inspect();
  await waitFor(() => expect(window.drDownload.inspectMedia).toHaveBeenCalledWith({ url: "https://example.com/video", cookie_source: "none" }));
});

test("open-file failures are visible on the download card", async () => {
  installApi({ listDownloads: jest.fn().mockResolvedValue([{ id: "old", title: "Archivo", status: "completed", filename: "C:\\missing.mp4" }]),
    openDownload: jest.fn().mockRejectedValue(new Error("El archivo ya no existe")) });
  render(<App />);
  await screen.findByText("MOTOR LOCAL LISTO");
  fireEvent.click(screen.getByRole("button", { name: "Historial" }));
  fireEvent.click(screen.getByRole("button", { name: "Abrir archivo" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("El archivo ya no existe");
});

test("English mode translates structured backend failures and all workflow labels", async () => {
  installApi({ getConfig: jest.fn().mockResolvedValue({ language: "en", cookie_source: "none", cookie_consent: false,
    output_dir: "C:\\Downloads", default_format: "video" }),
    inspectMedia: jest.fn().mockRejectedValue({ detail: { code: "format_unavailable", message: "Formato no disponible", recovery: "Elige otro formato" } }) });
  render(<App />);
  await screen.findByText("LOCAL ENGINE READY");
  fireEvent.change(screen.getByLabelText("Video link"), { target: { value: "https://example.com/video" } });
  fireEvent.click(screen.getByRole("button", { name: "Inspect link" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("The selected format is no longer available");
  expect(screen.queryByText("ENLACE")).not.toBeInTheDocument();
  expect(screen.queryByText("OUTPUT PATCH")).not.toBeInTheDocument();
});

test("changing the browser requires fresh consent before reading its session", async () => {
  installApi({ getConfig: jest.fn().mockResolvedValue({ language: "es", cookie_source: "edge", cookie_consent: true,
    notifications: false, output_dir: "C:\\Downloads", default_format: "video" }) });
  render(<App />);
  await screen.findByText("MOTOR LOCAL LISTO");
  fireEvent.click(screen.getByRole("button", { name: "Ajustes" }));
  fireEvent.change(screen.getByLabelText("Sesión del navegador"), { target: { value: "firefox" } });
  expect(screen.getByRole("button", { name: "Autorizar uso" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Nueva descarga" }));
  await inspect();
  expect(window.drDownload.inspectMedia).toHaveBeenCalledWith({ url: "https://example.com/video", cookie_source: "none" });
});

test("revoking consent prevents new cookie reads even when saving fails", async () => {
  installApi({ getConfig: jest.fn().mockResolvedValue({ language: "es", cookie_source: "edge", cookie_consent: true,
    notifications: false, output_dir: "C:\\Downloads", default_format: "video" }),
    updateConfig: jest.fn().mockRejectedValue(new Error("No se pudo guardar la revocación")) });
  render(<App />);
  await screen.findByText("MOTOR LOCAL LISTO");
  fireEvent.click(screen.getByRole("button", { name: "Ajustes" }));
  fireEvent.click(screen.getByRole("button", { name: "Revocar autorización" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo guardar la revocación");
  fireEvent.click(screen.getByRole("button", { name: "Nueva descarga" }));
  await inspect();
  expect(window.drDownload.inspectMedia).toHaveBeenCalledWith({ url: "https://example.com/video", cookie_source: "none" });
});

test("queueing rechecks consent after destination validation completes", async () => {
  let resolveDirectory;
  installApi({ getConfig: jest.fn().mockResolvedValue({ language: "es", cookie_source: "edge", cookie_consent: true,
    notifications: false, output_dir: "C:\\Downloads", default_format: "video" }),
    validateDirectory: jest.fn().mockResolvedValueOnce({ accepted: true, path: "C:\\Downloads", free_bytes: 500000000 })
      .mockImplementationOnce(() => new Promise((resolve) => { resolveDirectory = resolve; })) });
  render(<App />);
  await inspect();
  fireEvent.click(screen.getByRole("button", { name: "Agregar a la cola" }));
  fireEvent.click(screen.getByRole("button", { name: "Ajustes" }));
  fireEvent.click(screen.getByRole("button", { name: "Revocar autorización" }));
  await screen.findByText("Autorización revocada");
  await act(async () => resolveDirectory({ accepted: true, path: "C:\\Downloads", free_bytes: 500000000 }));
  expect(window.drDownload.createDownload.mock.calls[0][0].cookie_source).toBe("none");
});
