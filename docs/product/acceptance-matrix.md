# Matriz de aceptación por historia

Estados: `covered` tiene evidencia automatizada suficiente; `partial` tiene cobertura incompleta; `blocked` depende de un gate externo. Ningún `partial` o `blocked` puede pasar a release comercial.

| Historia | Evidencia automatizada actual | E2E/manual obligatorio | Estado | Gap o bloqueo |
|---|---|---|---|---|
| US-001 | directory service + API + React | primer arranque Windows | partial | aceptación Windows limpia |
| US-002 | directory service + React | ruta bloqueada/unidad ausente | partial | matriz Windows |
| US-003 | React preflight | recuperación conservando inspección | partial | E2E específico |
| US-004 | API estructurada | payload renderer manipulado | partial | prueba abuso Electron |
| US-010 | inspect API + IPC URL | inspección real controlada | partial | E2E-US-010 |
| US-011 | normalización + inspect API | tarjeta accesible real | partial | E2E-US-011 |
| US-012 | filtrado y formato desconocido | audio/vídeo reales | partial | E2E-US-012 |
| US-013 | consentimiento + errores sesión | Edge/Firefox abierto/cerrado | partial | E2E-US-013 |
| US-020 | queue + recuperación + API | dos tareas y reinicio | partial | E2E-US-020 |
| US-021 | parser + progress endpoint + UI | métricas y fases reales | partial | E2E-US-021 |
| US-022 | kill timeout + UI cancel | árbol de procesos real | partial | GAP-US-022-API/E2E |
| US-023 | retry API + mismo ID sin duplicado | fallo controlado y reintento | partial | E2E-US-023 |
| US-024 | nombre postprocesado + FFmpeg | FFprobe audio/vídeo | partial | GAP-US-024-FFPROBE |
| US-025 | shutdown workers + endpoint | cierre con transferencia y árbol de procesos | partial | MAN-US-025 pending |
| US-030 | SQLite + migración + recuperación | reinicio con tres estados | partial | E2E-US-030 |
| US-031 | file-actions + UI por ID | abrir archivo real | partial | E2E-US-031 |
| US-032 | file-actions + UI por ID | abrir Explorer | partial | E2E-US-032 |
| US-033 | delete API + preservación de archivo | preservar archivo real | partial | E2E-US-033 |
| US-040 | redacción + consentimiento + token | escáner de secretos exportados | partial | E2E-US-040 |
| US-041 | contrato IPC + sender/frame/navegación | renderer abusivo empaquetado | partial | E2E de abuso |
| US-042 | token API | inspección de listener loopback | partial | GAP-US-042-LISTENER |
| US-043 | logs en userData + exportación redactada | exportación empaquetada | partial | E2E-US-043 |
| US-050 | PyInstaller/NSIS + FFmpeg/Node incluidos | Windows limpio físico o VM, sin Python/Node externos | partial | matriz Windows limpia |
| US-051 | checksum + promoción + espera activa | actualización N→N+1 | partial | E2E-US-051 |
| US-052 | checksum inválido + retry interval | rollback app/NSIS | partial | GAP-US-052-APP |
| US-053 | NSIS construido | firma e instalación limpia | blocked | certificado Authenticode |
| US-054 | contrato de preservación | desinstalar NSIS exacto y comparar archivo | blocked | MAN-US-054 pending; smoke instalado aún no existe |
| US-060 | flujos React parciales | teclado, lector, contraste, escalas y movimiento reducido | partial | MAN-US-060 pending |
| US-061 | cambio de idioma React | recorrido completo ES/EN y reinicio | partial | MAN-US-061 pending |
| US-062 | workflow-ux.test.jsx: lecturas, inspección, navegación, encolado y pie; ejecución verde pendiente | backend interrumpido, borrador y cola real ES/EN | partial | MAN-US-062 pending |
| US-063 | workflow-ux.test.jsx: presets y espacio; API/IPC y FFprobe pendientes | codecs H.264/AAC, espacio y tamaño desconocido | partial | MAN-US-063 pending |
| US-064 | workflow-ux + preload-errors: recuperación, idioma y rechazo IPC message/detail; aceptación pendiente | errores reales y diagnóstico redactado ES/EN | partial | MAN-US-064 pending |
| US-065 | workflow-ux + API/queue/engine: consentimiento por fuente, revocación y recheck; persistencia real pendiente | fallo de guardado/navegación, cambio de navegador, revocación, cola y retry | partial | MAN-US-065 pending |
| US-066 | workflow-ux.test.jsx: búsqueda, estado y repetición; ejecución verde pendiente | repetir con archivos protegidos y filtros ES/EN | partial | MAN-US-066 pending |

El responsable de QA cambia el estado únicamente después de enlazar evidencia reproducible en `docs/qa/traceability-matrix.md`.
