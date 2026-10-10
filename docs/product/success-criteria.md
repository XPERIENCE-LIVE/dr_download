# Criterios de éxito y salida

Este documento convierte el objetivo comercial en condiciones verificables. Una métrica sin evidencia no se considera cumplida.

## Éxito funcional

| Criterio | Umbral | Evidencia obligatoria |
|---|---:|---|
| Flujo de descarga autorizado | 100% del flujo inspeccionar → encolar → completar en smoke controlado | reporte de smoke y archivo reproducible |
| Destino | 0 descargas enviadas con `DirectoryCheck.accepted=false` | prueba API + E2E |
| Cancelación | 0 procesos `yt-dlp`/FFmpeg huérfanos después de cancelar | prueba de proceso y logs |
| Historial | 100% de completados apuntan al archivo real existente | SQLite + prueba de integración |
| Recuperación | reinicio conserva cola e historial sin duplicar entradas | prueba de reinicio |
| Estados veraces | 0 disponibilidades no confirmadas, porcentajes de inspección o tamaños ficticios | pruebas de lectura/pending/fallo y MAN-US-062 |
| Continuidad | enlace, inspección y selección conservados al navegar durante la sesión | prueba de navegación y MAN-US-062 |
| Formato compatible | 100% de resultados del preset compatible comprobados son MP4 H.264/AAC; ausencia rechazada sin sustitución | API/IPC + FFprobe y MAN-US-063 |
| Preflight estimado | 0 tareas creadas con espacio inferior a max(128 MiB, dos veces estimated_bytes válido); 0 valores inválidos admitidos | límites API/IPC y MAN-US-063 |
| Recuperación y persistencia | 0 éxitos ficticios de guardado; 0 nuevas operaciones con cookies tras revocación o consentimiento fallido | pruebas de errores/config y MAN-US-064/065 |
| Historial y repetición | búsqueda por los tres campos y estado cumple todos los casos declarados; repetición permitida con 0 archivos previos sobrescritos | pruebas de filtro/aviso, hashes y MAN-US-066 |

## Éxito de calidad

- Todas las pruebas unitarias, integración y E2E aprobadas en CI.
- Cero defectos críticos o altos abiertos.
- Cada historia tiene trazabilidad requisito → contrato → prueba → evidencia.
- No existen secretos, cookies, tokens, URLs sensibles ni rutas privadas en logs.
- Lint, build y empaquetado reproducibles desde un checkout limpio.

## Éxito de seguridad y privacidad

- Renderer sin Node, sin acceso directo a filesystem y con CSP activa.
- Backend escuchando solo en `127.0.0.1` y protegido por token de sesión.
- Navegación externa bloqueada salvo acciones explícitas.
- Actualización con checksum, health check, reemplazo atómico y rollback.

## Éxito de distribución

- Instalación limpia en Windows 10/11 x64 sin Python ni Node instalados.
- Desinstalación conserva descargas del usuario.
- La publicación pública requiere firma Authenticode verificable; sin certificado solo se permite build interna.

## Regla de decisión

Si un criterio no tiene umbral y evidencia, queda `pending`. Nunca se sustituye evidencia por una afirmación verbal.
