# ADN de ingeniería de Dr. Download

Este contrato es normativo para personas, IA, CI y releases. Si una regla no puede demostrarse, su estado es `pending`; nunca se presume cumplida.

## Código de producción real

- El producto opera en modo **fail-closed**: si falta un runtime, binario, permiso, contrato o artefacto, detiene esa operación con un error estructurado y accionable.
- **Sin fallbacks de producción:** queda prohibido cambiar silenciosamente a otro motor, runtime, API, formato, ruta, archivo, interfaz o comportamiento.
- **Sin placeholders:** quedan prohibidos `TODO`, `FIXME`, `NotImplementedError`, pantallas de sustitución, datos ficticios y controles sin implementación final.
- Todo código incorporado debe ser el código final que ejecutará el binario comercial en la configuración declarada.
- Las migraciones compatibles son transformaciones explícitas, versionadas y probadas; no son rutas alternativas permanentes.

## Evidencia real

- **Sin simulaciones como evidencia de aceptación o release.** Mocks, stubs, monkeypatches y dobles controlados solo aíslan una unidad; jamás prueban que el producto instalado funciona.
- Una historia solo puede quedar `accepted` con evidencia producida por los procesos, binarios, filesystem, SQLite, IPC y red reales que correspondan a su nivel de aceptación.
- La evidencia identifica versión, commit, sistema operativo, arquitectura, configuración, fecha, comando, código de salida y SHA-256 de los artefactos relevantes.
- Una prueba externa variable, como YouTube, demuestra el resultado observado para esa fecha y configuración; no garantiza el comportamiento futuro del proveedor.

## Prohibiciones operativas

- No omitir gates, reducir aserciones, capturar fallos para devolver éxito ni reutilizar evidencia de otro commit.
- No declarar “100 %” sin definir el universo comprobado. La afirmación válida es: “100 % de los criterios declarados para esta versión y matriz tienen evidencia aprobada”.
- No publicar directamente en `main`. Todo cambio entra por Pull Request con checks bloqueantes y revisión de evidencia.
- No publicar instaladores sin Authenticode `Valid`, hashes, SBOM, avisos de terceros y matriz Windows aprobada.

## Gates normativos del feedback loop

- `QA-GATE-PR-001` — Todo cambio entra por Pull Request. `main` rechaza push directo y force-push y exige checks bloqueantes, CODEOWNERS y al menos una aprobación humana.
- `QA-GATE-ARTIFACT-001` — GitHub Actions alojado por GitHub construye una sola vez el instalador candidato. Ese mismo artefacto se prueba, firma y publica; recompilar entre etapas invalida el candidato.
- `QA-GATE-RELEASE-UNSIGNED-001` — Antes de SignPath, el gate de release prueba el artefacto unsigned, fija su SHA-256 y registra `publishable: false`.
- `QA-GATE-EVIDENCE-001` — Cada etapa emite evidencia machine-readable con commit, tag, run, artifact-id, SHA-256, matriz, timestamps y códigos de salida. Evidencia de otro SHA, artefacto o configuración no es reutilizable.
- `QA-GATE-APPROVAL-001` — Una persona revisora aprueba la PR y un `release approver` aprueba firma y publicación. Ninguna automatización puede concederse a sí misma una excepción o publicar por sí sola.
- `QA-GATE-SIGN-001` — Solo después de que SignPath devuelve el artefacto firmado, un gate post-SignPath verifica origen, SHA-256 signed, timestamp y Authenticode `Valid`; **SignPath Foundation** es el publisher visible. La ausencia de cualquiera bloquea la release.
- `QA-GATE-PUBLISH-001` — Solo puede publicarse el hash firmado que superó la validación post-firma. Tags y releases son inmutables; nunca se reemplaza un binario bajo la misma versión.
- `QA-GATE-ROLLFORWARD-001` — Un defecto publicado se recupera desde el último tag bueno mediante una versión de parche superior que repite PR, build, pruebas, SignPath, instalación y aprobación. No se reutilizan firmas ni evidencia.
- `QA-GATE-ACCEPTANCE-001` — La publicación permanece bloqueada hasta que todas las historias del alcance vigente estén aceptadas con evidencia real o exista una reducción de scope aprobada, además de SBOM/licencias completos y matriz Windows 10/11 aprobada. El universo vigente se deriva de las fichas y debe coincidir exactamente con ambas matrices.

La validación de Authenticode pertenece exclusivamente a `QA-GATE-SIGN-001`, después de recibir el artefacto firmado; nunca forma parte del gate unsigned previo.

Un fallo en cualquier `QA-GATE-*` conserva o restablece el estado `blocked`; nunca degrada el requisito ni convierte evidencia parcial en aceptación.

## Veracidad de experiencia

El [contrato aprobado US-062–US-066](../product/experience-reliability.md) obliga a confirmar disponibilidad por lecturas y guardado por respuesta, separar inspección indeterminada de encolado, nombrar tamaños desconocidos y traducir causa/recuperación por código. El preset compatible exige H.264/AAC MP4 sin fallback; estimaciones no confiables se validan en IPC/API y no eliminan permisos ni defensa de archivos. Cookies requieren consentimiento confirmado y revocación para operaciones futuras. La ampliación local de historial tiene [ADR-003](../architecture/adr/ADR-003-experience-and-history.md); no autoriza el backlog ni altera gates. No marcar una historia aceptada por añadir documentación o pruebas aisladas.

Consentimiento se valida estrictamente para la fuente persistida vigente en cada nueva lectura, incluyendo cola/retry/worker/comando. Una revocación no guardada bloquea nuevas peticiones UI pero no se declara persistida ni aplicada al backend. Errores transportados por IPC/contextBridge conservan un objeto simple message/detail; consumidores no dependen de propiedades de Error para traducir causa y recuperación.
