# ADR-002 — Política de carpeta de salida

**Decisión:** la carpeta predeterminada es `%USERPROFILE%\\Downloads\\Dr. Download`; se crea automáticamente y se valida con una escritura temporal y espacio mínimo de 128 MB.

**Motivo:** evita que el usuario reciba un error técnico después de inspeccionar el medio y mantiene la defensa en backend.
