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
