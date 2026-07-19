# Dr. Download

Aplicación privada para Windows que inspecciona, organiza y descarga contenido multimedia mediante yt-dlp. La interfaz Electron/React administra un backend FastAPI local; los datos, preferencias e historial permanecen en el equipo.

## Funciones

- Inspección previa con título, autor, duración, miniatura y formatos.
- Carpeta de destino creada y validada automáticamente antes de encolar.
- Audio MP3/original y video con la mejor calidad disponible.
- Cola, progreso automático, velocidad, ETA, cancelar y reintentar.
- Historial SQLite, apertura del archivo o carpeta y notificaciones nativas.
- Español e inglés; cookies de Edge, Firefox o modo sin cookies.
- Motor externo yt-dlp actualizable con verificación SHA-256 y rollback atómico.
- Renderer aislado: IPC enumerado, token de sesión, sandbox y CSP.

Descarga únicamente contenido que tengas autorización para guardar. Dr. Download no elude DRM.

## Desarrollo

Configuración de ingeniería validada: Python 3.13, Node.js 22 y Windows 10/11 x64. FFmpeg, FFprobe y Node se usan desde los recursos versionados del proyecto; no se cambia silenciosamente al software instalado en el equipo.

```powershell
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
npm install --prefix electron
npm run build --prefix electron
npm start --prefix electron
```

La primera descarga usa `%USERPROFILE%\\Downloads\\Dr. Download` si no se ha elegido otra carpeta. La aplicación comprueba permisos y espacio antes de encolar y ofrece una recuperación visible si Windows deniega el acceso.

En Windows también puede ejecutarse `electron\run_progressia_downloader.cmd`. Electron inicia el backend en un puerto dinámico y lo detiene al cerrar.

El empaquetado ejecuta `prepare:runtime`: incluye Node.js para yt-dlp, FFmpeg/FFprobe y el backend PyInstaller. El equipo del usuario no necesita Python ni Node externos. Los logs rotativos viven en `userData/logs`; desde Ajustes se exporta un diagnóstico acotado con URLs, tokens y rutas privadas redactadas.

## Pruebas

El gate bloqueante de Pull Request ejecuta contratos, pruebas, lint y build con un solo comando:

```powershell
npm run quality:pr
```

El gate de release es un superconjunto y además exige paquete real, smoke de audio/vídeo, FFprobe, SHA-256 y firma Authenticode válida:

```powershell
npm run quality:release
```

No existen opciones para omitir pasos. La evidencia se escribe en `artifacts/quality` y solo es válida para el commit y configuración declarados.

```powershell
python -m pytest -q --basetemp .pytest-local
npm test --prefix electron -- --runInBand
npm run lint --prefix electron
npm run build --prefix electron
```

Prueba real autorizada (primero inspección, luego descarga opcional):

```powershell
python tools/smoke_test_download.py "https://youtu.be/ID" --cookie-source edge
python tools/smoke_test_download.py "https://youtu.be/ID" --mode audio --cookie-source edge
```

## Instalador Windows

```powershell
python -m pip install -r backend/requirements-build.txt
npm run package:win --prefix electron
```

El resultado se crea en `electron/release`. Para una publicación real:

1. Revisar y, cuando corresponda, actualizar los binarios FFmpeg/FFprobe incluidos y sus hashes.
2. Configurar el certificado de firma admitido por electron-builder.
3. Definir `DR_DOWNLOAD_UPDATE_OWNER` y `DR_DOWNLOAD_UPDATE_REPO` para el repositorio de GitHub Releases.
4. Completar los avisos de terceros y probar instalación/actualización en Windows 10 y 11.

## Arquitectura y documentación

- [Producto](docs/product/product-requirements.md)
- [Sistema visual](docs/design/design-system.md)
- [Arquitectura](docs/architecture/architecture.md)
- [Publicación Windows](docs/release/windows-release.md)
- [Guía de uso](docs/user-guide.md)
- [Seguridad](SECURITY.md) · [Privacidad](PRIVACY.md) · [Terceros](THIRD_PARTY_NOTICES.md)
- [ADN de ingeniería](docs/engineering/project-dna.md) · [Estrategia de pruebas](docs/qa/test-strategy.md)

Licencia: [MIT](LICENSE).
