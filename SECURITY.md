# Security

Report vulnerabilities privately to the project owner; do not include cookies, tokens or downloaded content in a report.

The application loads only packaged UI resources, keeps the renderer sandboxed, exposes an enumerated IPC bridge and protects its loopback API with an ephemeral token. Browser cookies are read on demand by yt-dlp and are never persisted by Dr. Download.

Public releases must use a current supported Electron version, a signed installer, verified yt-dlp/FFmpeg binaries and dependency audits. Never disable sandbox, context isolation, CSP or signature verification to work around a release problem.

