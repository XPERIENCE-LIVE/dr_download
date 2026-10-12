# Backlog diferido

Estos elementos no son criterios satisfechos ni controles que deban aparecer habilitados. Requieren aprobación de alcance y ficha/matriz antes de implementar.

| Solicitud | Motivo de diferir | Condición para retomarla |
|---|---|---|
| Pegar varios enlaces | Cambia validación, resumen y errores por elemento; el flujo actual admite uno | Diseñar resultado por enlace, duplicados parciales y consentimiento; probar encolado sin pérdida ni duplicación |
| Reordenar cola | Cambia orden persistido y coordinación con una ejecución activa | Definir transacción y restricciones; demostrar orden tras reinicio y concurrencia |
| Pausar/reanudar transferencia | Cancelación y limpieza de staging actuales no conservan un punto seguro de reanudación | Definir retención segura, compatibilidad del motor y recuperación; probar hash final, reinicio y espacio |
| Cuentas/nube/sincronización | Amplía privacidad y rompe el límite local actual | ADR, modelo de amenazas y consentimiento antes de diseñar |
| Reordenar ítems de una lista de reproducción | Cambia el orden persistido de `playlist_items` y su coordinación con una lista en reproducción | Definir transacción de posiciones; probar orden tras reinicio y durante reproducción |
| Reproducción aleatoria y repetición de listas | No es necesaria para la primera versión de US-072 | Definir orden sin repeticiones y su estado tras saltar ítems no disponibles |
| Reproducir emisiones en directo | Sin duración ni seek por desplazamiento; el modelo de US-067/US-068 no aplica | Diseño específico de buffer y latencia; ADR si cambia la entrega |
| Picture-in-Picture | Cambia ventanas y políticas de Electron bloqueadas hoy | Revisar `setWindowOpenHandler`, foco y accesibilidad; pruebas de seguridad |
| Descargar una lista completa | Encola muchas tareas a la vez; equivale a pegado múltiple | Mismo diseño por elemento que «Pegar varios enlaces» |
| IA y reescritura de aplicación | No son necesarios para resolver estos flujos | Evidencia de una necesidad que la estructura actual no puede atender |

La búsqueda/filtro local y el aviso no prohibitivo de repetición ya tienen aprobación: [ADR-003](../architecture/adr/ADR-003-experience-and-history.md). No forman parte de este backlog diferido. La reproducción, las listas locales y su importación por enlace tienen aprobación en [ADR-004](../architecture/adr/ADR-004-streaming-playback-and-playlists.md); importar una lista no autoriza «Pegar varios enlaces».
