# ADR-002 — Política de carpeta de salida

**Decisión:** la carpeta predeterminada es `%USERPROFILE%\\Downloads\\Dr. Download`; se crea automáticamente y se valida con una escritura temporal y espacio mínimo de 128 MB.

**Motivo:** evita que el usuario reciba un error técnico después de inspeccionar el medio y mantiene la defensa en backend.

**Extensión aprobada 2026-10-08:** [ADR-003](ADR-003-experience-and-history.md) añade estimación opcional estricta para elevar el espacio requerido a `max(128 MiB, 2 * estimated_bytes)`. No cambia carpeta predeterminada, permisos, escritura temporal ni protección de archivos; sin estimación conserva el mínimo.
