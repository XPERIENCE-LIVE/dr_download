import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

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
    notify: jest.fn(),
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

test("changing the inspected URL requires a new inspection before queueing", async () => {
  installApi();
  render(<App />);
  const input = await screen.findByLabelText("Enlace del video");
  fireEvent.change(input, { target: { value: "https://youtu.be/first" } });
  fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));
  await screen.findByText("Video de prueba");
  fireEvent.change(input, { target: { value: "https://youtu.be/second" } });
  expect(screen.queryByText("Video de prueba")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Agregar a la cola" })).not.toBeInTheDocument();
});

test("Enter cannot start another inspection while the first is pending", async () => {
  installApi({ inspectMedia: jest.fn(() => new Promise(() => {})) });
  render(<App />);
  const input = await screen.findByLabelText("Enlace del video");
  fireEvent.change(input, { target: { value: "https://youtu.be/first" } });
  fireEvent.keyDown(input, { key: "Enter" });
  fireEvent.keyDown(input, { key: "Enter" });
  expect(window.drDownload.inspectMedia).toHaveBeenCalledTimes(1);
});

describe("automatic download refresh", () => {
  beforeEach(() => { jest.useFakeTimers(); installApi(); });
  afterEach(() => { jest.useRealTimers(); });

  const advance = async (milliseconds) => {
    await act(async () => { jest.advanceTimersByTime(milliseconds); });
  };

  test("refreshes active transfers and reports their completion", async () => {
    const listDownloads = jest.fn()
      .mockResolvedValueOnce([{ id: "live", title: "Transferencia", status: "downloading", progress: 10 }])
      .mockResolvedValue([{ id: "live", title: "Transferencia", status: "completed", progress: 100 }]);
    installApi({ listDownloads });
    render(<App />);
    await advance(0);
    expect(screen.getByText("TRANSFERENCIA ACTIVA")).toBeInTheDocument();
    await advance(1500);
    expect(screen.queryByText("TRANSFERENCIA ACTIVA")).not.toBeInTheDocument();
    expect(window.drDownload.notify).toHaveBeenCalledTimes(1);
  });

  test("avoids overlapping reads when the backend responds slowly", async () => {
    let resolveInitial;
    installApi({ listDownloads: jest.fn(() => new Promise((resolve) => { resolveInitial = resolve; })) });
    const { unmount } = render(<App />);
    await advance(30000);
    expect(window.drDownload.listDownloads).toHaveBeenCalledTimes(1);
    unmount();
    await act(async () => { resolveInitial([]); });
    await advance(30000);
    expect(window.drDownload.listDownloads).toHaveBeenCalledTimes(1);
  });

  test("uses fewer reads while idle", async () => {
    render(<App />);
    await advance(0);
    for (let index = 0; index < 6; index += 1) await advance(1500);
    expect(window.drDownload.listDownloads).toHaveBeenCalledTimes(1);
    await advance(1000);
    expect(window.drDownload.listDownloads).toHaveBeenCalledTimes(2);
  });

  test("does not render the application again for an unchanged history", async () => {
    const renders = jest.fn();
    installApi({ listDownloads: jest.fn().mockImplementation(async () => [{ id: "old", status: "completed", progress: 100 }]) });
    render(<React.Profiler id="app" onRender={renders}><App /></React.Profiler>);
    await advance(0);
    const initialRenders = renders.mock.calls.length;
    await advance(10000);
    expect(renders).toHaveBeenCalledTimes(initialRenders);
  });

  test("reduces background reads and refreshes immediately when the window returns", async () => {
    const hidden = jest.spyOn(document, "hidden", "get").mockReturnValue(true);
    try {
      render(<App />);
      await advance(0);
      await advance(10000);
      expect(window.drDownload.listDownloads).toHaveBeenCalledTimes(1);
      hidden.mockReturnValue(false);
      await act(async () => { document.dispatchEvent(new Event("visibilitychange")); });
      expect(window.drDownload.listDownloads).toHaveBeenCalledTimes(2);
    } finally { hidden.mockRestore(); }
  });

  test("a late history response cannot remove a newly queued download", async () => {
    let resolveHistory;
    installApi({ listDownloads: jest.fn().mockResolvedValueOnce([])
      .mockImplementationOnce(() => new Promise((resolve) => { resolveHistory = resolve; }))
      .mockResolvedValue([{ id: "task-1", status: "queued", progress: 0 }]) });
    render(<App />);
    await advance(0);
    await advance(10000);
    const input = screen.getByLabelText("Enlace del video");
    await act(async () => {
      fireEvent.change(input, { target: { value: "https://youtu.be/example" } });
      fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));
    });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Agregar a la cola" })); });
    expect(screen.getByText("TRANSFERENCIA ACTIVA")).toBeInTheDocument();
    await act(async () => { resolveHistory([]); });
    expect(screen.getByText("TRANSFERENCIA ACTIVA")).toBeInTheDocument();
  });

  test("recovers after an initial read failure without replaying old notifications", async () => {
    installApi({ listDownloads: jest.fn().mockRejectedValueOnce(new Error("Sin conexión"))
      .mockResolvedValue([{ id: "old", status: "completed", progress: 100 }]) });
    render(<App />);
    await advance(0);
    expect(screen.getByRole("alert")).toHaveTextContent("Sin conexión");
    await advance(10000);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(window.drDownload.notify).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Permitir cookies" })).not.toBeInTheDocument();
  });

  test("notifies completion of a task queued before the first history read finishes", async () => {
    let resolveInitial;
    installApi({ listDownloads: jest.fn()
      .mockImplementationOnce(() => new Promise((resolve) => { resolveInitial = resolve; }))
      .mockResolvedValue([{ id: "task-1", title: "Video de prueba", status: "completed", progress: 100 }]) });
    render(<App />);
    await advance(0);
    const input = screen.getByLabelText("Enlace del video");
    await act(async () => {
      fireEvent.change(input, { target: { value: "https://youtu.be/example" } });
      fireEvent.click(screen.getByRole("button", { name: "Analizar enlace" }));
    });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Agregar a la cola" })); });
    await act(async () => { resolveInitial([]); });
    await advance(1500);
    expect(screen.queryByText("TRANSFERENCIA ACTIVA")).not.toBeInTheDocument();
    expect(window.drDownload.notify).toHaveBeenCalledTimes(1);
  });

  test("shows a refresh error and recovers on the next successful read", async () => {
    installApi({ listDownloads: jest.fn()
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error("Motor temporalmente desconectado"))
      .mockResolvedValue([]) });
    render(<App />);
    await advance(0);
    await advance(10000);
    expect(screen.getByRole("alert")).toHaveTextContent("Motor temporalmente desconectado");
    await advance(10000);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
