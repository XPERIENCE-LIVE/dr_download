# Épicas de producto

| ID | Épica | Historias | Resultado | Salida |
|---|---|---|---|---|
| E1 | Destino confiable | US-001, US-002, US-003, US-004 | Toda descarga tiene una carpeta validada | `DirectoryCheck`, preflight, errores accionables |
| E2 | Inspección y formatos | US-010, US-011, US-012, US-013 | El usuario conoce el medio antes de descargar | metadatos y formatos normalizados |
| E3 | Cola y ejecución | US-020, US-021, US-022, US-023, US-024, US-025 | Descargas observables, cancelables y recuperables | estados, progreso, reintento y apagado limpio |
| E4 | Historial y archivos | US-030, US-031, US-032, US-033 | El usuario encuentra y abre resultados reales | SQLite y acciones por ID |
| E5 | Seguridad y privacidad | US-040, US-041, US-042, US-043 | Ningún secreto sale del límite local | IPC endurecido y logs redactados |
| E6 | Distribución comercial | US-050, US-051, US-052, US-053, US-054 | Instalador verificable, actualizable y seguro al desinstalar | NSIS firmado, checksum, rollback y preservación de descargas |
| E7 | Experiencia accesible y localizada | US-060, US-061 | El producto es operable con accesibilidad de Windows en español e inglés | teclado, foco, AA, escalado, movimiento reducido e i18n completa |

Cada historia debe enlazar una prueba automatizada y una evidencia de aceptación.
