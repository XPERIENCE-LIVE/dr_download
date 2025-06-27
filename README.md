# Progressia Media Downloader

## Backend Setup
```
pip install -r backend/requirements.txt
python -m py_compile backend/*.py
```
Optionally set the `ALLOW_ORIGINS` environment variable to customize CORS
(comma-separated list). For development, the backend defaults to allowing
`http://localhost:3000` and `http://localhost:5173`.

### Start the API server
```
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Frontend Setup
```
cd electron
npm install
npm run build
```

Create an `.env` file in the `electron` directory to override the backend URL:

```
VITE_API_BASE_URL=http://your-api-host:8000
```
If unset, the Electron app defaults to `http://localhost:8000`.

## Running

```
cd electron
npm start
```

Running `npm start` as the `root` user fails because Electron requires the
`--no-sandbox` flag in that scenario. Whenever possible, run the application as
a normal user. For advanced cases where running as `root` is unavoidable, pass
the flag explicitly:

```
npm start -- --no-sandbox
```

When the Electron UI starts, the output path field is empty by default. Use the
**Choose...** button to pick a download directory through the OS folder dialog.

## Basic API Usage
Start a download by posting a URL to `/download/` and store the returned
`task_id`:

```
POST http://localhost:8000/download/
{"url": "https://example.com/video"}
```

Query progress with that identifier:

```
GET http://localhost:8000/progress/<task_id>
```

## License
This project is licensed under the [MIT License](LICENSE).
