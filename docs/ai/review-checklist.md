# Checklist de revisión

- [ ] Cumple la historia exacta.
- [ ] La prueba fallaba antes del cambio.
- [ ] No hay rutas, cookies o tokens expuestos.
- [ ] IPC y filesystem permanecen aislados.
- [ ] Estados y errores son observables.
- [ ] Regresión completa ejecutada.
- [ ] Documentación y trazabilidad actualizadas.
- [ ] Lecturas, inspección, encolado y guardado muestran estados reales; desconocido nunca se presenta como cero o progreso inventado.
- [ ] Causa/recuperación, presets, fases y acciones completos ES/EN; recuperación conserva enlace, ID y archivos según operación.
- [ ] estimated_bytes validado en IPC/API; compatible comprobado H.264/AAC MP4 sin sustitución silenciosa.
- [ ] Consentimiento fallido bloquea cookies; revocación confirmada impide nuevas operaciones y persiste.
- [ ] Fuente distinta exige autorización nueva; API HTTP403, cola/retry/worker/comando revalidan consentimiento persistido. Revocación fallida no se presenta como cambio backend confirmado.
- [ ] IPC/contextBridge conserva detalle mediante objeto transferible message/detail; UI traduce código conocido y usa mensaje seguro para desconocido.
- [ ] Búsqueda/filtro/aviso aprobados por ADR-003; repetición intencional permitida con defensa contra sobrescritura.
- [ ] Estados de fichas/matrices/ledger no exceden evidencia; auditorías históricas intactas.
