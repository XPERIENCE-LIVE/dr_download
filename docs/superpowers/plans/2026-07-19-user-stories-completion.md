# User Stories Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir US-010–US-053 en fichas completas y sincronizar aceptación y trazabilidad.

**Architecture:** `user-stories.md` es la fuente canónica. `acceptance-matrix.md` expresa el estado por historia y `traceability-matrix.md` enlaza contrato, pruebas, evidencia y release. Los gaps usan IDs estables para que otra IA pueda implementar TDD sin reinterpretación.

**Tech Stack:** Markdown, pytest, Jest, Electron smoke, Windows manual matrix.

## Global Constraints

- No afirmar cobertura que no exista.
- Una fila por historia.
- Mantener IDs US-010–US-053 estables.
- Producto open source, sin servicio de pago obligatorio.

---

### Task 1: Fichas canónicas

**Files:**
- Modify: `docs/product/user-stories.md`

**Interfaces:**
- Consumes: épicas E2–E6 y nombres de pruebas existentes.
- Produces: 21 fichas con los 13 campos obligatorios.

- [x] Extraer nombres de pruebas existentes.
- [x] Escribir cada ficha y asignar `GAP-*` donde no hay cobertura.
- [x] Verificar IDs únicos y campos obligatorios.

### Task 2: Aceptación individual

**Files:**
- Modify: `docs/product/acceptance-matrix.md`

**Interfaces:**
- Consumes: fichas canónicas.
- Produces: estado automatizado/manual por historia.

- [x] Crear una fila US-010–US-053.
- [x] Marcar `partial`, `blocked` o `covered` usando evidencia real.

### Task 3: Trazabilidad individual

**Files:**
- Modify: `docs/qa/traceability-matrix.md`

**Interfaces:**
- Consumes: IDs de historia, endpoints, símbolos y pruebas.
- Produces: trazabilidad requisito → prueba → evidencia.

- [x] Crear una fila por historia.
- [x] Ejecutar escaneo de IDs/campos y comprobar que no existen historias resumidas.

No se crea commit porque este workspace no está inicializado como repositorio Git.
