# ADR-001 — Motor externo único y obligatorio

**Decisión:** usar exclusivamente el `yt-dlp.exe` empaquetado/actualizado. Si el ejecutable, Node o FFmpeg requerido no está disponible, la operación falla de forma estructurada; no existe un segundo motor.

**Motivo:** permite actualizar el extractor sin reinstalar, mantiene una frontera de proceso cancelable y evita que una ruta alternativa o una versión diferente produzca resultados no verificados.

**Riesgo:** yt-dlp, el runtime JavaScript y FFmpeg deben distribuirse y validarse antes de publicar. La ausencia de cualquiera bloquea el release.
