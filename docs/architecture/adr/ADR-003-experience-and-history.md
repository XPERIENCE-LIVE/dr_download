# ADR-003 — Experiencia confiable y búsqueda de historial

**Estado:** aprobado por producto el 2026-10-08; implementación y aceptación tienen estados separados.

**Contexto:** el usuario necesita saber qué operación ocurre, elegir un archivo comprensible, recuperar fallos y encontrar descargas anteriores sin perder su preparación.

**Decisión:** aplicar el [contrato de experiencia confiable](../../product/experience-reliability.md), incluida la ampliación de alcance para buscar por título/URL/archivo, filtrar por estado y advertir enlaces repetidos. La repetición intencional sigue permitida. No se modifican las defensas contra colisiones de archivos. US-062–US-066 y sus matrices contienen la aceptación medible; no se omite ningún gate.

**Consecuencias:** la búsqueda y el aviso usan los datos locales ya cargados; no introducen dependencia, servicio o contrato remoto. El borrador vive solo en memoria. El preset compatible requiere H.264/AAC en MP4 sin fallback. La estimación de tamaño mejora el preflight, pero no garantiza espacio futuro ni tamaño final.

**Diferido:** pegado múltiple, reordenar cola y pausa/reanudación real requieren decisiones y pruebas adicionales; se registran en el [backlog](../../product/backlog.md). Cuentas, nube, IA y reescritura permanecen fuera de alcance.
