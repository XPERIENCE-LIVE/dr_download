# Sistema visual — Estudio profesional

## Identidad

La interfaz toma referencias de monitores de señal y equipos de estudio. La firma es una línea segmentada con un punto ámbar que indica el avance de inspección, transferencia y procesamiento.

## Tokens

| Rol | Valor |
|---|---|
| Vacío | `#0B0D10` |
| Grafito | `#12161C` |
| Panel mineral | `#191F27` |
| Línea | `#2D3743` |
| Marfil | `#F1EEE6` |
| Cobalto | `#6385FF` |
| Ámbar | `#F4B860` |
| Error | `#EF6B73` |

Tipografía: Segoe UI Variable para interfaz y Cascadia Mono para datos. Radio máximo de 7 px; bordes finos y sombras profundas solo para separar planos.

## Componentes y estados

- Navegación lateral: etiqueta, icono lineal, indicador activo y contador de cola.
- Composer: enlace, acción de inspección y línea de señal.
- Media card: miniatura real, metadatos, formato y carpeta.
- Download card: estado, progreso, telemetría y acciones contextuales.
- Error: mensaje directo más una recuperación concreta.
- Vacío: invita a crear una descarga, sin decoración innecesaria.

Todos los controles tienen foco de 2 px ámbar. Las transiciones se eliminan con `prefers-reduced-motion`.

## Estados y decisiones de descarga

La línea de inspección indica actividad indeterminada sin porcentaje. Inspección, encolado y guardado tienen etiquetas y estados separados, anunciados con semántica accesible. El pie prioriza la ejecución y traduce fases. Los datos desconocidos se etiquetan como desconocidos. Después de encolar existe **Ver cola / View queue**.

La selección principal muestra vídeo compatible, mejor vídeo y MP3 con descripciones de resultado; audio original y streams técnicos se agrupan en expansión avanzada accesible. Las acciones de recuperación aparecen junto a la causa traducida; un cambio pendiente de ajustes no recibe confirmación de éxito. Historial incluye búsqueda, estado y limpieza de filtros; el aviso de enlace repetido permite continuar. El [contrato de experiencia](../product/experience-reliability.md) es la fuente de comportamiento, y [copy ES/EN](error-copy.md) la guía de errores.

