# Plan de implementación de descargas recuperables

**Objetivo:** aplicar las mejoras aprobadas en el flujo existente y enviarlas a GitHub mediante rama y PR, conservando los gates de release.

**Diseño:** [descargas claras y recuperables](../specs/2026-10-08-reliable-workflows-design.md). Se ejecutan en paralelo dominios con archivos separados; la integración y revisión final pertenecen al agente principal.

## Restricciones globales

Sin nuevas bibliotecas, datos sensibles en logs, pérdida de archivos ni aceptación ficticia. Prueba roja antes de cambios no triviales. Preservar IPC y API existentes; campos nuevos opcionales compatibles. Actualizar dependencias existentes si bloquean el gate, con regresión completa. No integrar directamente en main ni publicar instalador.

## Entregables y verificación

- [x] Interfaz: `electron/src/App.jsx`, `i18n.js`, `styles/main.css`; regresiones React en `src/__tests__/workflow-ux.test.jsx`. Probar conectividad fallida, borrador, progreso indeterminado, encolado, errores/recuperación, consentimiento, búsqueda, filtros y duplicados. Mantener polling sin solapamientos.
- [x] Motor: `backend/media_service.py`, `engine_runner.py`, `main.py`, IPC y pruebas correspondientes. Probar selección compatible estricta, estimación de audio/vídeo, validación de enteros y rechazo por espacio. Mantener presets antiguos y nombres sin colisiones.
- [x] Documentación: ADR aprobado, requisitos, historias/matrices, CLAUDE.md, ADN, guardrails, guía y contratos. Ejecutar validador contractual; historias con evidencia parcial siguen sin aceptación.
- [ ] Validación instalada: scripts existentes con identidad explícita del artefacto y smoke de navegación real. Ejecutar solo instalaciones aisladas, sin tocar datos/instalación del usuario; reportar matrices o firma no disponibles.
- [x] Integración: revisar diff completo; pytest, Jest, lint, build y gate PR; corregir fallos reales sin reducir aserciones.
- [x] GitHub: commit del código y documentos, push de rama, PR con alcance y evidencia, verificar SHA remoto. No emitir release ni integrar main.

## Foco de revisión

Consentimiento fallido no habilita cookies; navegación durante una promesa no pierde datos; elegir carpeta no envía una ruta previa; historial y barra seleccionan fases verdaderas; estimaciones desconocidas nunca se anuncian como conocidas; errores ES/EN y operaciones rechazadas quedan visibles.

## Verificación de integración

215 pruebas Python y 90 Jest pasan después de actualizar Jest/Babel-Jest/jsdom a 30.5.2 y las versiones compatibles del lockfile. Validador contractual, lint y build pasan. Auditoría npm: cero altas/críticas; 26 moderadas transitivas en herramientas de desarrollo, ninguna en dependencias de producción. No se aplica `audit fix --force`, que propone degradar electron-builder. El fingerprint del gate incluye los scripts de smoke.

La revisión de las correcciones de consentimiento y transporte de errores no encontró fallos importantes adicionales. El smoke empaquetado y el gate PR del commit definitivo se registrarán por separado; instalación/desinstalación y firma requieren la matriz Windows aislada.

El gate local PR pasó sobre `fe24c8b`; la rama y PR #90 ya están en GitHub. CI detectó peers opcionales ausentes en el lockfile generado por npm 11: se reprodujo el fallo con npm 10.9.9, se regeneró el lockfile con esa versión y su `npm ci --dry-run` pasó. El primer smoke quedó bloqueado antes de UI por `ELECTRON_RUN_AS_NODE` heredado del host; el launcher limpia esa variable solo para el hijo y restaura el entorno, con regresión ejecutada. La repetición final usa un paquete reconstruido y hashes propios; no reutiliza el resultado bloqueado como aceptación.
