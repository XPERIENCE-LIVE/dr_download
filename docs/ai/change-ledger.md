# Registro anti-regresión y anti-duplicación

Este registro evita que una IA vuelva a “corregir” un problema ya resuelto o reintroduzca una regresión.

## Identidad de un cambio

Cada defecto o historia usa un ID estable (`BUG-###`, `US-###`) y registra:

`ID | síntoma | causa raíz | archivos | prueba roja | commit/build | prueba verde | evidencia | estado`

La identidad no se basa en texto libre: se conserva el ID aunque cambie la redacción.

## Protocolo obligatorio antes de modificar

1. Buscar el ID, el síntoma y los símbolos afectados en este registro y en la matriz de trazabilidad.
2. Ejecutar la prueba de regresión asociada en estado actual.
3. Si la prueba pasa, no modificar producción por ese defecto: investigar si existe una regresión distinta y abrir otro ID.
4. Si falla, registrar la salida fresca y demostrar que la causa es la misma antes de editar.
5. Una corrección solo se cierra con prueba roja observada, prueba verde y regresión completa.

## Estado y bloqueo

- `open`: no resuelto.
- `fixed`: prueba verde y evidencia adjunta.
- `verified`: regresión completa y aceptación manual aprobadas.
- `wont-fix`: decisión de producto documentada en ADR.
- `reopened`: solo si una prueba previamente verde falla de nuevo; enlazar la evidencia nueva.

## Entrada inicial

Las entradas siguientes conservan el registro histórico de trabajo, no certifican estado actual ni evidencia válida para este SHA. El estado verificable vigente está en `change-ledger.json`: sus entradas permanecen `open` hasta evidencia aprobada del mismo commit. Los conteos históricos no deben reutilizarse como aceptación.

`BUG-001 | Output directory not writable | ruta inexistente/no escribible no validada antes de encolar | directory_service, API, React | test_directory_service + App.test.jsx | build 2.1.0 | 96 pytest + 31 Jest | smoke empaquetado real de audio/vídeo y API validate | fixed; pendiente de aceptación Windows limpia`

`GAP-US-050-NODE | runtime JavaScript externo | yt-dlp recibía node sin ruta | runtime-paths, engine_runner, media_service, package | tests Node RED | build 2.1.0 | runtime Node v22.14.0 incluido + packaged smoke | FFprobe y NSIS | fixed; pendiente VM limpia`

`GAP-US-041-ELECTRON | seguridad no comprobable | políticas embebidas sin unidad testeable | electron-security, electron.js | módulo ausente RED | build 2.1.0 | sender main-frame, sandbox y navegación probados | 31 Jest | fixed`

`GAP-US-043-ROTATION | logs en cwd y sin exportación | ruta relativa no apta para paquete | utils, diagnostics, preload, UI | tests de ruta/redacción/export RED | build 2.1.0 | logs userData y reporte acotado/redactado | 96 pytest + 31 Jest | fixed; pendiente E2E de exportación instalada`

`QUALITY-001 | contratos no ejecutables y validaciones dispersas | documentación sin gate único | contract_validator, quality-gate, workflows, ledger | tests de validadores RED | workspace 6E36D58B... | gate PR verde; gate release recorre paquete y descargas reales y bloquea Authenticode NotSigned | artifacts/quality/quality-pr.json + quality-release.json | fixed; publicación bloqueada por US-053`

## Experiencia confiable — 2026-10-08

US-062–US-066 tienen fingerprints y regresiones independientes en el ledger JSON. Su [contrato](../product/experience-reliability.md) enlaza decisiones, límites y casos manuales. Estado `open`: implementación/pruebas aisladas no sustituyen evidencia de aceptación Windows; no se inventan SHA, build ni resultados. ADR-003 aprueba la ampliación de historial sin cerrar historias ni gates. El [backlog](../product/backlog.md) conserva solicitudes diferidas y sus condiciones de entrada.
