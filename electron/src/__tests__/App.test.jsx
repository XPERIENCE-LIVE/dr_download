import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import App, { findNewCompletions } from "../App";


const metadata = {
  title: "Video de prueba",
  author: "Canal",
  duration: 90,
  thumbnail: "https://example.com/thumb.jpg",
  formats: [
    { id: "video-best", kind: "video", label: "Mejor calidad", container: "mp4" },
    { id: "audio-mp3", kind: "audio", label: "MP3 · 192 kbps", container: "mp3" }
  ]
};

function installApi(overrides = {}) {
  window.drDownload = {
    getConfig: jest.fn().mockResolvedValue({
      language: "es",
      cookie_source: "edge",
      cookie_consent: true,
      notifications: true,
      output_dir: "C:\\Downloads",
      default_format: "video"
    }),
    updateConfig: jest.fn().mockResolvedValue({ status: "ok" }),
    validateDirectory: jest.fn().mockResolvedValue({ accepted: true, valid: true, path: "C:\\Downloads", writable: true }),
    listDownloads: jest.fn().mockResolvedValue([]),
    inspectMedia: jest.fn().mockResolvedValue(metadata),
    createDownload: jest.fn().mockResolvedValue({ id: "task-1", status: "queued", progress: 0 }),
    selectFolder: jest.fn().mockResolvedValue("D:\\Media"),
    cancelDownload: jest.fn().mockResolvedValue({ id: "task-1", status: "cancelled" }),
    retryDownload: jest.fn(),
    deleteDownload: jest.fn(),
    openPath: jest.fn(),
    openDownload: jest.fn(),
    exportDiagnostics: jest.fn().mockResolvedValue(true),
    ...overrides
  };
}

test("exports local diagnostics from settings", async () => {
  installApi();
  render(<App />);
  await screen.findByRole("heading", { name: "Nueva descarga" });
  fireEvent.click(screen.getByRole("button", { name: "Ajustes" }));
  fireEvent.click(screen.getByRole("button", { name: "Exportar diagnóstico" }));
  await waitFor(() => expect(window.drDownload.exportDiagnostics).toHaveBeenCalled());
});

describe("Dr. Download premium shell", () => {
  beforeEach(() => installApi());

  test("shows Spanish navigation and no manual progress control", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Nueva descarga" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cola" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Historial" })).toBeInTheDocument();
    expect(screen.queryByText("Check Progress")).not.toBeInTheDocument();
    expect(screen.getByText("MOTOR LOCAL LISTO")).toBeInTheDocument();
  });

  test("keeps the active transfer strip visible across the application", async () => {
    installApi({
      listDownloads: jest.fn().mockResolvedValue([
        {
          id: "task-live",
          title: "Transferencia de prueba",
          status: "downloading",
          progress: 42,
          speed_bps: 8400000,
          eta_seconds: 31,
          bytes_downloaded: 12000000
        }
      ])
    });

    render(<App />);

    expect(await screen.findByText("TRANSFERENCIA ACTIVA")).toBeInTheDocument();
    expect(screen.getByText("Transferencia de prueba")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ajustes" }));
    expect(screen.getByText("TRANSFERENCIA ACTIVA")).toBeInTheDocument();
  });

  test("inspects a URL and adds the selected media to the queue", async () => {
    render(<App />);
    const input = await screen.findByLabelText("Enlace del video");
    fireEvent.change(input, { target: { value: "https://youtu.be/example" } });
    fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));

    expect(await screen.findByText("Video de prueba")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Agregar a la cola" }));

    await waitFor(() => expect(window.drDownload.createDownload).toHaveBeenCalledWith({
      url: "https://youtu.be/example",
      format_id: "video-best",
      output_dir: "C:\\Downloads",
      cookie_source: "edge"
    }));
    expect(await screen.findByText("En cola")).toBeInTheDocument();
  });

  test("confirms the queue even when the worker races past 'queued' before the response arrives", async () => {
    installApi({
      // The single background worker can pick up the task before this
      // resolves, so the backend may already report a later status.
      createDownload: jest.fn().mockResolvedValue({ id: "task-1", status: "inspecting", progress: 0 })
    });
    render(<App />);
    const input = await screen.findByLabelText("Enlace del video");
    fireEvent.change(input, { target: { value: "https://youtu.be/example" } });
    fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));

    expect(await screen.findByText("Video de prueba")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Agregar a la cola" }));

    await waitFor(() => expect(window.drDownload.createDownload).toHaveBeenCalled());
    expect(await screen.findByText("En cola")).toBeInTheDocument();
  });

  test("validates the destination before queueing", async () => {
    installApi({
      validateDirectory: jest.fn().mockResolvedValue({
        accepted: false,
        valid: false,
        path: "C:\\Blocked",
        writable: false,
        error_code: "access_denied",
        recovery: "Elige otra carpeta"
      })
    });
    render(<App />);
    const input = await screen.findByLabelText("Enlace del video");
    fireEvent.change(input, { target: { value: "https://youtu.be/example" } });
    fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));
    expect(await screen.findByText("Video de prueba")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar a la cola" })).toBeDisabled();
    expect(await screen.findByText("Elige otra carpeta")).toBeInTheDocument();
    expect(window.drDownload.createDownload).not.toHaveBeenCalled();
  });

  test("does not read browser cookies before explicit consent", async () => {
    installApi({
      getConfig: jest.fn().mockResolvedValue({
        language: "es",
        cookie_source: "edge",
        cookie_consent: false,
        notifications: true,
        output_dir: "C:\\Downloads",
        default_format: "video"
      })
    });

    render(<App />);
    const input = await screen.findByLabelText("Enlace del video");
    fireEvent.change(input, { target: { value: "https://youtu.be/example" } });
    fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));

    await waitFor(() => expect(window.drDownload.inspectMedia).toHaveBeenCalledWith({
      url: "https://youtu.be/example",
      cookie_source: "none"
    }));
  });

  test("changes the interface language from settings", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Nueva descarga" });
    fireEvent.click(screen.getByRole("button", { name: "Ajustes" }));
    fireEvent.change(screen.getByLabelText("Idioma"), { target: { value: "en" } });
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
  });

  test("cancels an active queued download", async () => {
    installApi({
      listDownloads: jest.fn().mockResolvedValue([
        { id: "task-1", title: "Trabajo activo", status: "queued", progress: 0 }
      ])
    });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Cola" }));
    fireEvent.click(await screen.findByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(window.drDownload.cancelDownload).toHaveBeenCalledWith("task-1"));
  });

  test("opens completed files by download identifier instead of renderer paths", async () => {
    installApi({
      listDownloads: jest.fn().mockResolvedValue([
        {
          id: "task-1",
          title: "Trabajo terminado",
          status: "completed",
          progress: 100,
          filename: "C:\\Downloads\\video.mp4",
          output_dir: "C:\\Downloads"
        }
      ])
    });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Historial" }));
    fireEvent.click(await screen.findByRole("button", { name: "Abrir archivo" }));
    fireEvent.click(await screen.findByRole("button", { name: "Abrir carpeta" }));

    expect(window.drDownload.openDownload).toHaveBeenNthCalledWith(1, "task-1", "file");
    expect(window.drDownload.openDownload).toHaveBeenNthCalledWith(2, "task-1", "folder");
  });
});

test("completion detection ignores historical items and reports transitions", () => {
  const current = [{ id: "a", status: "completed" }, { id: "b", status: "completed" }];
  expect(findNewCompletions({ a: "downloading" }, current).map((item) => item.id)).toEqual(["a"]);
});
