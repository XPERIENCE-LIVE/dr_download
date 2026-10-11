# Dr. Download production completion implementation plan

**Goal:** Deliver a hardened, interactive and verifiably packaged Windows application.

**Method:** Incremental extraction with test-driven development. No new runtime dependency unless the standard library or current stack cannot satisfy a demonstrated requirement.

## Phase 1 — Reproducible baseline

1. Preserve the current green baseline: Python tests, Jest, lint and Vite build.
2. Add production-audit tests for every observed defect before changing production code.
3. Add a controlled smoke-test script that starts a backend on a free port, authenticates, inspects, downloads, polls and probes outputs.

## Phase 2 — Motor and persistence

1. Test and fix inspection parity so the external engine uses the supported JavaScript runtime.
2. Test and filter non-media formats such as MHTML/storyboards.
3. Test and remove frozen-runtime JSON writes while retaining idempotent JSON-to-SQLite migration.
4. Test startup recovery for queued and interrupted records.
5. Test observable lifecycle transitions and structured error mapping.
6. Extract executor/state/coordinator seams without changing route contracts.
7. Test updater interval, checksum, health check, atomic promotion and rollback.

## Phase 3 — Local API and Electron security

1. Add failing tests for invalid IPC identifiers, oversized payloads, notification text and arbitrary file paths.
2. Replace `openPath(path)` with identifier-based file/folder actions.
3. Validate IPC payload schemas and preserve trusted-sender checks.
4. Add disk-space/output-folder preflight and normalized API errors.
5. Make shutdown semantics explicit and verify Electron terminates the backend cleanly.

## Phase 4 — Real Deck nocturno UI

1. Add interaction tests for every navigation destination and primary action.
2. Build the approved Deck nocturno layout in the actual React tree.
3. Connect inspection, format selection, folder selection, queue, history and settings.
4. Add automatic progress, structured recovery messages, file actions and notifications.
5. Complete Spanish/English strings, keyboard behavior, focus states and reduced-motion support.
6. Delete the separate static mock and unused legacy component only after reference checks and green tests.

## Phase 5 — End-to-end and packaging

1. Add a real Electron smoke harness covering preload, IPC, API startup and backend shutdown.
2. Rebuild the backend executable and NSIS artifact.
3. Run the authorized audio/video fixture and validate outputs with FFprobe.
4. Run Edge, Firefox and no-cookie tests; classify environmental failures precisely.
5. Verify install, update preparation and uninstall preservation on available Windows hosts.
6. Record signing and unavailable-host requirements as release blockers rather than claiming success.

## Phase 6 — Documentation and release evidence

1. Update README, architecture, product requirements, design system, release guide and user guide.
2. Update SECURITY, PRIVACY, third-party notices and changelog.
3. Produce a final verification table with command, result, artifact and environment.

## Verification commands

- `python -m pytest -q --basetemp=<unique workspace folder>`
- `npm test -- --runInBand`
- `npm run lint`
- `npm --prefix electron run build`
- controlled backend smoke script for the authorized media fixture
- `ffprobe` validation for generated MP3 and MP4 files
- `npm --prefix electron run package:win`

