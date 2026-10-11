# Windows launcher

## Goal

Provide a double-click Windows launcher that prepares and runs the complete Dr. Download application instead of opening Electron without its backend or compiled frontend.

## Entry point

Keep `electron/run_progressia_downloader.cmd` as the user-facing entry point. It delegates to a PowerShell script in the same directory so process startup, readiness checks, errors, and cleanup can be handled reliably.

## Startup flow

1. Resolve the repository root from the script location so launching works from any current directory.
2. Verify that Python, Node.js, and npm are available; stop with a clear message if any is missing.
3. Install Python requirements only when required imports are unavailable.
4. Install frontend packages only when `electron/node_modules` is missing.
5. Build the React frontend so Electron can load `electron/dist/public/index.html`.
6. Start `python -m backend.main` as a hidden child process from the repository root.
7. Poll `http://127.0.0.1:8000/config/` with a bounded timeout. If startup fails, show the backend log/output and stop.
8. Run Electron in the foreground.
9. In a `finally` block, stop only the backend process created by this launcher.

## Error handling

Every external command must be checked for a nonzero exit status. The launcher must leave the console open with a readable error when invoked by double-click, while returning a failure code for scripted use. Backend cleanup must run after Electron exits or any later startup step fails.

## Verification

Add a non-GUI check mode to exercise dependency checks, frontend build, backend startup, health polling, and cleanup without opening Electron. Verify that the backend process is no longer running afterward. Then run the existing Python and React tests, lint, and production build.
