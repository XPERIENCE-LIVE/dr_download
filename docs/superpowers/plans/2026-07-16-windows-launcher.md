# Windows Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a double-click Windows launcher that builds and starts the backend and Electron application with reliable cleanup.

**Architecture:** Keep the existing CMD file as a thin user-facing wrapper and put orchestration in one PowerShell script. A pytest integration check invokes a non-GUI mode and verifies successful backend readiness and cleanup.

**Tech Stack:** Windows CMD, PowerShell 5+, Python 3.10+, pytest, Node.js, npm, Electron.

## Global Constraints

- Keep Electron 28.
- Do not use forced dependency upgrades.
- Stop only the backend process created by the launcher.
- Launch successfully from any current working directory.

---

### Task 1: Launcher integration check

**Files:**
- Create: `tests/test_windows_launcher.py`
- Create: `electron/run_progressia_downloader.ps1`
- Modify: `electron/run_progressia_downloader.cmd`

**Interfaces:**
- Consumes: `python -m backend.main`, `npm run build`, and `npm start`.
- Produces: `run_progressia_downloader.ps1 -CheckOnly`, returning exit code 0 and printing `LAUNCHER_CHECK_OK` after the backend becomes ready.

- [ ] **Step 1: Write the failing integration test**

Create a Windows-only pytest test that runs `powershell.exe -NoProfile -ExecutionPolicy Bypass -File electron/run_progressia_downloader.ps1 -CheckOnly`, expects exit code 0 and `LAUNCHER_CHECK_OK`, and confirms port 8000 is closed afterward.

- [ ] **Step 2: Verify the test fails**

Run: `python -m pytest tests/test_windows_launcher.py -q --basetemp=.pytest-launcher-red`

Expected: FAIL because `electron/run_progressia_downloader.ps1` does not exist.

- [ ] **Step 3: Implement the launcher**

Create a PowerShell coordinator that validates tools, installs missing dependencies, builds React, starts the backend hidden, polls `/config/`, optionally launches Electron, and stops its backend in `finally`. Replace the CMD body with a call to that script and pause only on errors.

- [ ] **Step 4: Verify the launcher and regression suite**

Run the launcher test, all Python tests, root npm tests, lint, build, and Python compilation. Expected: all commands return exit code 0.

- [ ] **Step 5: Record repository limitation**

No commit step is available because this directory does not contain `.git` metadata.
