# Privacy

Dr. Download processes links, browser-session access, downloads, preferences and history locally. It contains no accounts, advertising, analytics, telemetry or cloud synchronization.

When authorized, yt-dlp reads the selected browser profile only for inspection/download. Dr. Download does not copy or store cookies. Logs rotate locally and must not contain tokens or raw cookie values. Downloaded files remain in the folder selected by the user.

Browser access requires consent confirmed by a successful settings save. Failed consent persistence does not authorize access. Consent can be revoked in Settings for future operations; revocation does not promise to interrupt a transfer already started. The New download draft remains in memory during navigation and is not automatically persisted across application restarts. History search and duplicate-link warnings use locally loaded records without sending them to another service.

Authorization applies only to the browser source saved with strictly true consent. Switching sources requires fresh permission; inspection/creation requests without matching persisted authorization are rejected. Queueing, retries, workers and engine commands recheck current persisted authorization and use no cookies after confirmed revocation or source change. If saving revocation fails, the UI blocks new browser-enabled inspection/creation and offers retry, while the backend retains the last saved configuration; failed persistence does not guarantee revocation after restart.

Removing the application preserves user data by default; delete the Dr. Download application-data folder manually if complete removal is desired.

