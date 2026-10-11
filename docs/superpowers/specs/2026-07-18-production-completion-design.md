# Dr. Download production completion design

**Date:** 2026-07-18
**Status:** Approved for implementation by the user's production-completion request

## Goal

Turn the current Windows MVP into a production-capable application whose real Electron UI, local API, download engine, persistence, and packaged artifacts are verified together. A static visual prototype is not an acceptance artifact.

## Product boundary

- Windows 10/11 x64, Electron + React + FastAPI + SQLite.
- Individual downloads, one-worker queue, history, settings, local notifications, Edge/Firefox/no-cookie modes.
- No DRM bypass, accounts, payments, cloud sync, telemetry, or media library.
- Deck nocturno becomes the real interactive React application after engine hardening.

## Engine and state design

- Extract the monolithic worker incrementally into an executor, state/error translator, and queue coordinator while retaining the public API.
- Use only the external verified `yt-dlp.exe`; a missing engine is an explicit blocking error.
- Pass the same supported JavaScript runtime options to inspection and download operations.
- Normalize only real audio/video formats; reject storyboard, image and MHTML entries.
- Persist queue and history in SQLite. JSON is migration input only and is never written in a frozen build.
- Persist explicit lifecycle states: `queued`, `inspecting`, `downloading`, `postprocessing`, `completed`, `failed`, `cancelled`.
- Mark interrupted active work as `failed` with code `interrupted`; queued work is re-enqueued at startup.
- Emit structured errors and preserve safe diagnostic details without URLs, cookies, tokens, or private paths.

## Electron security design

- Renderer access remains limited to frozen preload methods.
- Every IPC operation validates type, length, identifier shape, and trusted sender.
- File actions accept a download identifier and action, then resolve the recorded path in the main process/backend. Arbitrary absolute renderer paths are forbidden.
- Notification text is bounded and sanitized.
- Navigation and popups remain blocked; context isolation, sandbox and CSP remain enabled.
- Local API remains bound to `127.0.0.1` on a dynamic port with a random session token.

## User interface design

- Replace the current shell with the approved Deck nocturno system inside React, not in a separate HTML mock.
- Provide real navigation for Nueva descarga, Cola, Historial, Ajustes and Acerca de.
- Inspection displays metadata and valid formats; enqueueing transitions to the real queue.
- Poll automatically and show state, percentage, bytes, speed and ETA when supplied.
- Provide cancel, retry, remove, open file and open folder actions.
- Spanish is default and English is complete. Keyboard focus, AA contrast, semantic labels and reduced motion are required.

## Distribution design

- Package backend, `yt-dlp`, FFmpeg and FFprobe with no external Python/Node requirement.
- Engine updates verify SHA-256, perform a health check, replace atomically and keep a previous version.
- App updates remain disabled unless a valid GitHub release channel is configured; failures never block startup.
- NSIS builds preserve user data. Public release requires a signing certificate; unsigned output is explicitly internal.

## Acceptance evidence

- All Python, React, IPC, lint and production-build checks pass.
- Packaged backend authenticates requests and downloads the authorized fixture in audio and video modes.
- FFprobe confirms expected streams and non-zero duration.
- Edge, Firefox and no-cookie inspection results are recorded honestly.
- Electron end-to-end tests exercise real preload/IPC/backend boundaries, not only mocks.
- Installer behavior is tested on available Windows hosts; untested Windows versions remain an explicit release blocker.
