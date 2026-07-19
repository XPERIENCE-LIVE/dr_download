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
