# Backlog diferido

Estos elementos no son criterios satisfechos ni controles que deban aparecer habilitados. Requieren aprobación de alcance y ficha/matriz antes de implementar.

| Solicitud | Motivo de diferir | Condición para retomarla |
|---|---|---|
| Pegar varios enlaces | Cambia validación, resumen y errores por elemento; el flujo actual admite uno | Diseñar resultado por enlace, duplicados parciales y consentimiento; probar encolado sin pérdida ni duplicación |
| Reordenar cola | Cambia orden persistido y coordinación con una ejecución activa | Definir transacción y restricciones; demostrar orden tras reinicio y concurrencia |
| Pausar/reanudar transferencia | Cancelación y limpieza de staging actuales no conservan un punto seguro de reanudación | Definir retención segura, compatibilidad del motor y recuperación; probar hash final, reinicio y espacio |
| Cuentas/nube/sincronización | Amplía privacidad y rompe el límite local actual | ADR, modelo de amenazas y consentimiento antes de diseñar |
| IA y reescritura de aplicación | No son necesarios para resolver estos flujos | Evidencia de una necesidad que la estructura actual no puede atender |

La búsqueda/filtro local y el aviso no prohibitivo de repetición ya tienen aprobación: [ADR-003](../architecture/adr/ADR-003-experience-and-history.md). No forman parte de este backlog diferido.
