# Dr. Download

Aplicación privada para Windows que inspecciona, organiza y descarga contenido multimedia mediante yt-dlp. La interfaz Electron/React administra un backend FastAPI local; los datos, preferencias e historial permanecen en el equipo.

## Funciones

- Inspección previa con título, autor, duración, miniatura y formatos.
- Carpeta de destino creada y validada automáticamente antes de encolar.
- Presets de vídeo compatible MP4 H.264/AAC, mejor vídeo y MP3; audio original y streams bajo formatos avanzados.
- Cola, progreso automático, velocidad, ETA, cancelar y reintentar.
- Historial SQLite, apertura del archivo o carpeta y notificaciones nativas.
- Búsqueda local por título/enlace/archivo, filtro por estado y aviso de enlace repetido que permite repetir intencionalmente.
- Estado confirmado del servicio local, inspección sin porcentaje inventado y borrador conservado al navegar durante la sesión.
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

La primera descarga usa `%USERPROFILE%\\Downloads\\Dr. Download` si no se ha elegido otra carpeta. La aplicación comprueba permisos y espacio antes de encolar: mínimo 128 MiB o dos veces el tamaño estimado, lo que sea mayor. La estimación es asesoría; tamaño desconocido se indica explícitamente. Si Windows deniega acceso, ofrece causa y recuperación ES/EN. Ajustes solo confirma guardado tras respuesta y permite revocar consentimiento para nuevas operaciones con cookies.

En Windows también puede ejecutarse `electron\run_progressia_downloader.cmd`. Electron inicia el backend en un puerto dinámico y lo detiene al cerrar.

El empaquetado ejecuta `prepare:runtime`: incluye Node.js para yt-dlp, FFmpeg/FFprobe y el backend PyInstaller. El equipo del usuario no necesita Python ni Node externos. Los logs rotativos viven en `userData/logs`; desde Ajustes se exporta un diagnóstico acotado con URLs, tokens y rutas privadas redactadas.

## Pruebas

El gate bloqueante de Pull Request ejecuta contratos, pruebas, lint y build con un solo comando:

```powershell
npm run quality:pr
```

El contrato normativo del gate de release exige paquete real, smoke de audio/vídeo, FFprobe y SHA-256 del artefacto unsigned con `publishable: false`; la firma Authenticode `Valid` se verifica después de SignPath en una etapa independiente. La implementación actual y su evidencia deben revisarse contra [publicación Windows](docs/release/windows-release.md); ningún comando por sí solo autoriza publicar:

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
2. Completar el flujo SignPath Foundation y validar el artefacto firmado exacto con aprobación humana según los gates normativos.
3. Definir `DR_DOWNLOAD_UPDATE_OWNER` y `DR_DOWNLOAD_UPDATE_REPO` para el repositorio de GitHub Releases.
4. Completar los avisos de terceros y probar instalación/actualización en Windows 10 y 11.

## Arquitectura y documentación

- [Producto](docs/product/product-requirements.md)
- [Experiencia confiable US-062–US-066](docs/product/experience-reliability.md) · [Decisión aprobada](docs/architecture/adr/ADR-003-experience-and-history.md) · [Backlog diferido](docs/product/backlog.md)
- [Sistema visual](docs/design/design-system.md)
- [Arquitectura](docs/architecture/architecture.md)
- [Publicación Windows](docs/release/windows-release.md)
- [Guía de uso](docs/user-guide.md)
- [Seguridad](SECURITY.md) · [Privacidad](PRIVACY.md) · [Terceros](THIRD_PARTY_NOTICES.md)
- [ADN de ingeniería](docs/engineering/project-dna.md) · [Estrategia de pruebas](docs/qa/test-strategy.md)

Licencia: [MIT](LICENSE).

La documentación describe el contrato de producto. Las matrices conservan historias `partial` y casos Windows `pending`: las pruebas aisladas y un build interno no acreditan aceptación ni release comercial.
