# Test and dependency hardening

## Scope

- Make the root `npm test` setup step work without shell-specific syntax on Windows and Unix-like systems.
- Apply only dependency updates accepted by the existing semver ranges and `npm audit fix` without `--force`.
- Keep Electron 28; upgrading to Electron 43 is a separate migration because it is a breaking major-version change.

## Implementation

Replace the Unix-only directory check in the root `pretest` script with a small Node command that installs frontend dependencies only when `electron/node_modules` is missing. Keep the existing frontend test command unchanged.

Refresh `electron/package-lock.json` using the non-forced npm audit fix. Do not add packages or change application behavior.

## Verification

Run the root frontend test script on Windows, all Python tests with a repository-local pytest temporary directory, Python compilation, frontend lint, frontend production build, and a production dependency audit. Any Electron-only advisory that requires a forced major upgrade will be reported rather than hidden.
