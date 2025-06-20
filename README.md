# Progressia Media Downloader

## Backend Setup
```
pip install -r backend/requirements.txt
python -m py_compile backend/*.py
```
Set `ALLOW_ORIGINS` to customize CORS (comma-separated list). For development,
the backend defaults to allowing `http://localhost:3000` and `http://localhost:5173`.

## Frontend Setup
```
cd electron
npm install
npm run build
```

## Running

```
cd electron
npm start
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
