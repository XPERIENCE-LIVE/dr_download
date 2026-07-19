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

