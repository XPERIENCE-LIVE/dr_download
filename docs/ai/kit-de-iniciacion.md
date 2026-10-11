# Kit de iniciación para IA

Antes de tocar código: leer README, arquitectura, scope, criterios de éxito, `docs/engineering/project-dna.md`, guardrails, change ledger e historia; indexar el repositorio; localizar símbolos existentes; escribir prueba roja; ejecutar solo el alcance; implementar código final mínimo; ejecutar prueba verde y regresión; actualizar trazabilidad/changelog; reportar comandos y evidencia.

Si el ID ya está en estado `fixed` o `verified`, ejecutar primero su prueba. Solo abrir `reopened` si existe una regresión demostrable.

No crear rutas alternativas “temporales”, placeholders ni simulaciones de producto. Si falta una capacidad, implementar la capacidad final o devolver un error fail-closed. Los dobles de unidad nunca se registran como evidencia E2E/release.

Plantilla: objetivo, contexto, archivos permitidos, interfaces, prueba roja, implementación, regresión, aceptación, evidencia y riesgos.

Para esta iteración, leer también [experiencia confiable](../product/experience-reliability.md), ADR-003 y backlog; US-062–US-066 tienen estado parcial y evidencia real pendiente. Usar el grafo MCP para descubrir símbolos antes de búsquedas de código; CLAUDE.md enlaza las fuentes normativas sin sustituirlas.
