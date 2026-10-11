# Instrucciones de trabajo — Dr. Download

Aplicación local Windows Electron/React + FastAPI + yt-dlp/FFmpeg. Lee primero [ADN](docs/engineering/project-dna.md), [alcance](docs/product/scope.md), [guardrails](docs/ai/guardrails.md), [ledger](docs/ai/change-ledger.json) y la historia que vas a cambiar.

- Descubre código mediante codebase-memory-mcp: `search_graph`, `trace_path`, `get_code_snippet`, `query_graph`, `get_architecture`; usa búsquedas de archivos para documentación/configuración o cuando el grafo no baste.
- Conserva capas, helpers e IPC enumerado existentes. Haz el cambio mínimo completo en callers, contratos, pruebas y documentación; no añadas dependencias, wrappers ni reescrituras sin necesidad.
- Aplica el [contrato de experiencia](docs/product/experience-reliability.md) y [ADR-003](docs/architecture/adr/ADR-003-experience-and-history.md). No inventes disponibilidad, porcentajes, tamaños, éxito de guardado o compatibilidad; consentimiento y validaciones permanecen fail-closed.
- No implementes el [backlog diferido](docs/product/backlog.md), controles sin función, fallbacks silenciosos ni ampliaciones no aprobadas. Una advertencia de enlace repetido permite repetir y conserva la protección de archivos.
- La raíz y las carpetas de código solo contienen archivos versionados. Ejecuta pytest sin `--basetemp` (usa `build/pytest-tmp`) o con `build/pytest-<nombre>` si corres en paralelo; nunca `--basetemp=.pytest-*`. Ver [guardrails](docs/ai/guardrails.md).
- Cambia código de producción con prueba roja y verde verificables. Toda prueba declarada debe existir. Ejecuta el validador contractual y los checks correspondientes; `partial` y `pending` no significan aceptación.
- Mantén exactamente el mismo universo de historias en épicas, fichas, aceptación, trazabilidad y matriz manual. Nunca cambies auditorías históricas para ocultar un gap ni inventes ejecutor, SHA o evidencia.
- No publiques en `main`, no omitas gates ni marques evidencia de otro commit como actual. Las aprobaciones de producto no sustituyen revisión humana, firma ni aceptación de release.
- Conserva la ejecución directa en Windows con runtimes incluidos; VM/equipo físico limpio son entornos de prueba. El gate npm bloquea severidad moderada o superior, también en herramientas de desarrollo; no ocultes avisos mediante exclusiones o downgrades forzados.
- La prueba NSIS automatizada usa un runner desechable de GitHub y runtimes empaquetados; no instalar/desinstalar en el perfil habitual del mantenedor. Windows Server con herramientas fuera de PATH no acredita Windows 10/11 limpio. Firma requiere SignPath aprobado; no sustituirlo por firma autofirmada ni marcar release aprobada por la existencia del workflow.
- PR usa el smoke instalado `startup`; release fija `downloads` y exige las tres descargas reales. No reutilizar evidencia startup para firma ni declarar que probó descargas; los hitos y fallos externos se conservan por separado.
