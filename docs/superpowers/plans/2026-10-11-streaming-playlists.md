# Streaming and playlists implementation plan

> For agentic workers: use superpowers:executing-plans with independent domains delegated through superpowers:dispatching-parallel-agents. Keep each domain's red/green evidence and review the integrated branch.

**Goal:** implement US-067–US-072 so the desktop application plays YouTube/Vimeo streams and local/imported playlists.

**Architecture:** use the included yt-dlp executable to resolve metadata, FFmpeg to deliver fragmented MP4 through FastAPI, and a validated Electron dr-stream protocol. SQLite stores source links and playlist metadata; resolved media URLs remain in backend memory. React uses enumerated IPC methods and the existing design system.

**Tech stack:** existing Python/FastAPI/httpx/SQLite, Electron, React; no new dependencies.

**Spec:** [playback and playlists](../../product/playback-and-playlists.md), [ADR-004](../../architecture/adr/ADR-004-streaming-playback-and-playlists.md).

## Global constraints

- Preserve download APIs, history, strict cookie consent, local Windows runtimes, token isolation and existing release gates.
- No provider iframe, remote scripts, DRM bypass, live playback, on-disk media cache or speculative features.
- Resolve the review findings explicitly: seek takes a finite nonnegative decimal; playlist import uses a renderer-generated UUID request_id and cancelPlaylistImport(request_id), DELETE /playlists/import/{request_id}.
- No acceptance claims from isolated doubles; evidence records exact source identity, commands, outputs and limitations. Branch push is not release publication.

## Review focus

- Rapid seeking/changing videos must terminate only owned processes; an old disconnect must not stop the new stream.
- Revoked consent must prevent new cookie/segment lookups, including work resuming after an await.
- Corrupt or unwritable SQLite must fail visibly and preserve existing downloads.
- Oversized or canceled imports must not commit partial playlists, including cancellation just before commit.
- Source/provider failures must show translated cause and recovery and never become a success claim.

## Task 1 — playlists and atomic import

Files: backend/store.py, new backend/playlist_routes.py, backend/tests/test_playlists.py.

- [x] Write and run failing SQLite/API tests for CRUD, repeated URL, invalid names/URLs, unavailable items, >500 entries and cancel-before-commit.
- [x] Extend the existing store with playlists and playlist_items; retain downloads and migration behavior. Use one transaction for imported lists.
- [x] Implement APIRouter with GET/POST /playlists, PUT/DELETE /playlists/{uuid}, POST/DELETE items and POST /playlists/import plus DELETE /playlists/import/{request_id}. list returns [{id,name,items:[{id,url,title,duration,thumbnail,available}],created_at}]. add returns item with duplicate bool; import returns {playlist,imported,unavailable}.
- [x] Extract via included engine --flat-playlist, strict consent, bounded timeout and cancellation. Close subprocess pipes and terminate owned processes on failure/shutdown.
- [x] Run focused tests; record output under artifacts/quality/streaming-implementation.

## Task 2 — Electron protocol and bridge

Files: electron/ipc-contract.js, preload.js, backend-client.js, electron.js, package.json, new stream-protocol.js, index CSP and Jest tests.

- [x] Write red tests for UUID/seek/provider URL validation, unknown protocol forms, IPC methods and HTTP 204.
- [x] Add startPlayback(body), stopPlayback(id), listPlaylists(), createPlaylist({name}), renamePlaylist(id,{name}), deletePlaylist(id), addPlaylistItem(id,body), removePlaylistItem(id,itemId), importPlaylist(body), cancelPlaylistImport(requestId).
- [x] Register standard/secure/stream dr-stream before ready. Handle only dr-stream://play/{uuid}?start={finite decimal}&revision={integer}, forward authenticated localhost stream, preserve cancellation and error status, disable caching. CSP adds media-src 'self' dr-stream: only; package the module.
- [x] Run focused Jest tests and review trusted-sender and shutdown wiring.

## Task 3 — player and list views

Files: electron/src/App.jsx, i18n.js, styles.css, new components/Playback.jsx and components/Playlists.jsx, React tests.

- [x] Write red tests for ordered progression, skip notice, end-of-list stop, absolute/decimal seeking, stale resolution cleanup, SponsorBlock undo, list persistence/error/cancel flows.
- [x] Add player/list navigation and play/add controls after inspection using existing visual language and accessible native controls.
- [x] startPlayback returns {session_id,title,duration,height,sponsor_segments:[{start,end}],sponsor_status}; stream URL is composed only from session_id and start. Keep one playback session active, stop it on change/close, ignore stale results and dispose late sessions.
- [x] Add separate confirmed sponsorblock_consent preference (off by default). Failed saves never authorize lookups. Show provider/error recovery in ES/EN.
- [x] Run focused React tests, lint and build.

## Task 4 — streaming service and integration

Files: new backend/playback_service.py, playback_routes.py, backend/main.py, config.py, backend/tests/test_playback.py, real smoke script.

- [x] Write red tests for format selection, live/DRM, finite decimal seek, expiry, metadata redaction, cookies, SponsorBlock consent, and actual FFmpeg process cleanup.
- [x] Resolve allowed providers with included yt-dlp, choose supported H.264/VP9/AV1 + AAC/Opus without transcoding. Stream via owned FFmpeg subprocess with separate input headers and bounded IO. Return only safe metadata; expire sessions and clean process ownership deterministically.
- [x] Verify SponsorBlock engine behavior. Its explicit --sponsorblock-mark invocation returns chapters; ordinary inspection does not request them. Use existing httpx hash-prefix API as the primary separately consented lookup to enforce a 5 s bound, latest-consent check and the three supported categories, with visible failure.
- [x] Include both routers and shutdown cleanup; move blocking inspection off the event loop.
- [x] Run entire quality:pr, real Electron/FFmpeg/provider smoke and record timings, decode/progress, playlist operations and process cleanup. Build packaged candidate for applicable real checks; preserve external failures.

## Task 5 — documentation, review and delivery

- [x] Update API/IPC/spec/user guide and story test inventories to match implemented behavior. Preserve pending Windows/release acceptance where unverified.
- [x] Review all changed callers and boundaries; run the full gate after final code changes.
- Commit and push the feature branch only if its relevant checks pass. Do not publish an installer or merge main; no fabricated acceptance or evidence from another source identity.

Validation outcome: [execution report](../../qa/streaming-implementation-validation.md). A branch push is not a claim that all acceptance thresholds passed.
