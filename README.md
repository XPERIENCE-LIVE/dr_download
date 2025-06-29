# Dr. Download 2.0

Dr. Download 2.0 is a desktop application developed by **PROGRESSIA** for downloading audio or video content using [yt-dlp](https://github.com/yt-dlp/yt-dlp).  It consists of a FastAPI backend and an Electron+React frontend, providing a simple GUI and an HTTP API for programmatic access.

## Features
- Queue multiple downloads and monitor their progress.
- Choose between video or audio (MP3) output.
- Simple configuration stored in `backend/config.json`.
- Cross‑platform desktop UI built with Electron.

## Requirements
- Python 3.10 or newer
- Node.js 18 or newer
- `ffmpeg` available on your `PATH` for audio conversion

## Getting Started

### Backend Setup
1. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. (Optional) Compile the sources to check for syntax errors:
   ```bash
   python -m py_compile backend/*.py
   ```
3. You may set the environment variable `ALLOW_ORIGINS` to a comma‑separated list of hosts allowed for CORS. By default the backend allows `http://localhost:3000` and `http://localhost:5173`.
4. Start the API server from the repository root using module execution:
   ```bash
   python -m backend.main
   ```
   The `-m` flag is required because `backend/main.py` relies on package‑relative imports.

### Frontend Setup
1. Install Node dependencies:
   ```bash
   cd electron
   npm install
   ```
2. Build the React frontend:
   ```bash
   npm run build
   ```
   The generated `index.html` is located at `electron/dist/public/index.html`.
3. Create an `.env` file inside `electron` to override the API base URL if the backend runs elsewhere:
   ```
   VITE_API_BASE_URL=http://your-api-host:8000
   ```
   If omitted, the Electron app talks to `http://localhost:8000`.

### Running the Desktop App
From the `electron` directory run:
```bash
npm start
```
Running the app as `root` will fail with a sandbox error. Either invoke the command as a regular user or append `--no-sandbox` when running as `root`:
```bash
npm start -- --no-sandbox
```
When the UI appears, use **Choose...** to pick an output directory. The path field is empty by default.

On Windows you may double‑click `run_progressia_downloader.cmd` to install
any missing dependencies and launch Electron automatically. The script skips
`npm update` by default but you can enable it by setting the environment
variable `DD_RUN_NPM_UPDATE=1` before running the command.

### Linting
Check the React source code with ESLint. Make sure the Node dependencies are installed first:
```bash
cd electron
npm install
npm run lint
```
### Running Tests
Install [yt-dlp](https://github.com/yt-dlp/yt-dlp) together with the development
dependencies. The tests also require the `pytest_asyncio` plugin:
```bash
pip install pytest_asyncio -r backend/requirements.txt -r backend/requirements-dev.txt
pytest -q
```


## API Reference

### `POST /download/`
Start a new download.
```json
{ "url": "https://example.com/video", "format": "video", "output_dir": "/path/to/downloads" }
```
Response:
```json
{ "status": "queued", "task_id": "<uuid>" }
```

### `GET /progress/{task_id}`
Retrieve the current progress percentage for a task.

### `GET /history/`
List details of all queued and finished downloads.
Only the most recent 1000 entries are stored in `backend/history.json`.
Older records are automatically discarded when the file is saved.

### `GET /config/` and `POST /config/`
Read or update the contents of `backend/config.json`. Example default configuration:
```json
{
  "theme": "dark",
  "default_format": "video",
  "worker_threads": 4,
  "log_max_bytes": 1000000,
  "log_backup_count": 3
}
```

## Logs
Backend logs are written to `logs/backend.log` in addition to standard output.
By default the log file is rotated when it reaches **1&nbsp;MB** and up to
**3** old copies are kept. These limits can be adjusted via the
`log_max_bytes` and `log_backup_count` settings in `backend/config.json`.
Check this directory if you encounter issues.

## Packaging
After building the frontend you can package the application with tools such as `electron-packager` or `electron-builder` to create a standalone installer. The Electron app expects the build output in `electron/dist/public/index.html`, so ensure the `npm run build` step is executed before packaging. Packaging steps are not included in this repository.

## Contributing
Contributions and bug reports are welcome. Feel free to open an issue or PR.

## License
This project is licensed under the [MIT License](LICENSE).
