# Diseño — feedback loop, firma SignPath y rollback

Fecha: 2026-07-19  
Estado: aprobado conceptualmente; pendiente de revisión del documento  
Producto: Dr. Download 2.1.x para Windows 10/11 x64

## Decisiones fijadas

- `XPERIENCE-LIVE/dr_download` permanecerá público mientras use el patrocinio gratuito.
- El código se distribuirá bajo MIT y los componentes incluidos conservarán sus licencias y avisos.
- El editor visible de los instaladores firmados será **SignPath Foundation**.
- Solo GitHub Actions alojado por GitHub construirá el artefacto candidato a firma.
- Una release requiere aprobación humana; ninguna automatización publica por sí sola.
- El rollback de aplicación será un **roll-forward controlado**: revertir al último código bueno y publicar una versión de parche superior.

## Feedback loop obligatorio

### Pull Request

1. Todo cambio parte de una rama y entra mediante Pull Request.
2. `main` rechaza push directo y exige revisión más todos los checks.
3. El gate PR ejecuta, sobre el mismo commit:
   - validador contractual SDD y ledger anti-duplicación;
   - integridad de dependencias Python;
   - pruebas Python y Jest completas;
   - ESLint y build Vite;
   - auditoría npm bloqueante desde severidad alta.
4. Un fallo deja la PR bloqueada. No existen switches de omisión, éxito degradado ni aprobación por evidencia antigua.
5. La revisión humana confirma alcance, prueba roja, prueba verde, seguridad, privacidad, documentación y trazabilidad.

### Release candidata

1. La release nace de un tag inmutable sobre `main` aprobado.
2. GitHub Actions construye una sola vez backend PyInstaller, renderer y NSIS.
3. El gate release prueba ese artefacto con procesos reales: aplicación empaquetada, backend, SQLite, IPC, yt-dlp, FFmpeg y FFprobe.
4. La prueba controlada descarga audio y vídeo reales, comprueba streams, archivos no vacíos y ausencia de procesos huérfanos.
5. Se archivan commit, configuración, matriz, timestamps, códigos de salida y SHA-256.
6. El mismo artefacto aprobado se sube como artefacto de workflow y se envía a SignPath. Está prohibido recompilar entre pruebas y firma.
7. SignPath verifica el origen y requiere aprobación manual.
8. El artefacto firmado se descarga y debe cumplir Authenticode `Valid`; después se repiten validación de hash, instalación, inicio y desinstalación.
9. La publicación en GitHub Releases requiere aprobación humana final y evidencia Windows 10/11 aprobada.

## Evidencia y retroalimentación

- Cada ejecución produce evidencia machine-readable asociada al SHA del commit y al SHA-256 del instalador.
- El ledger usa un ID y fingerprint estables por cambio. Si la prueba registrada ya pasa, una IA no vuelve a modificar producción bajo el mismo defecto.
- Una evidencia unitaria no sustituye aceptación. Los mocks y stubs nunca certifican el artefacto instalado.
- Un fallo abre o reabre un ID, conserva la salida original y vuelve al ciclo prueba roja → corrección mínima → regresión.
- Solo puede afirmarse “100 %” para los criterios declarados de una versión y matriz concretas.

## Rollback y recuperación

### Antes de publicar

- Si falla cualquier gate, empaquetado, smoke, firma o verificación, el candidato no se publica.
- El artefacto fallido y sus diagnósticos se retienen como evidencia privada del workflow; la release estable no cambia.

### Después de publicar

1. Congelar inmediatamente el canal de actualización y marcar la versión afectada como retirada, sin borrar su auditoría.
2. Abrir un incidente con versión, hashes, alcance, síntomas y criterio de recuperación.
3. Crear una rama desde el último tag estable, revertir el cambio causante y asignar una versión de parche mayor; por ejemplo, `2.1.0` defectuosa se recupera mediante `2.1.1`.
4. Ejecutar nuevamente PR, release, SignPath, instalación y aprobación. Nunca reutilizar la firma ni evidencia anterior.
5. Publicar la versión corregida y restaurar el canal solo cuando todos los gates pasen.

No se fuerza un downgrade automático: puede romper datos o dejar equipos en versiones divergentes. El instalador estable anterior permanece disponible para recuperación manual documentada, mientras la solución distribuida es una versión superior firmada.

### Datos y motores

- Toda migración SQLite crea respaldo, es idempotente y se verifica antes de promover la nueva versión. Una migración destructiva requiere ADR y procedimiento de restauración probado.
- Si una actualización de yt-dlp falla checksum o health check, el reemplazo no se promueve y se conserva la última versión verificada.
- Si una instalación de aplicación falla, la instalación vigente y los datos del usuario se preservan; un fallo nunca elimina descargas.

## Controles de repositorio requeridos

- Protección de `main`: Pull Request obligatorio, al menos una aprobación y checks PR requeridos.
- MFA para responsables de GitHub y SignPath.
- `CODEOWNERS` para workflows, políticas SignPath, ADN, release y seguridad.
- Acciones de GitHub fijadas a versiones aprobadas y permisos mínimos.
- Entorno `production-release` protegido con aprobación manual.
- Política pública de firma en README con autores/revisores/aprobadores, privacidad y atribución a SignPath.
- Releases y tags inmutables; no reemplazar binarios bajo el mismo número de versión.

## Criterios de aceptación

- Una PR con cualquier gate fallido no puede integrarse.
- Un push directo a `main` es rechazado.
- Un release no puede publicarse sin aprobación humana y Authenticode `Valid`.
- El SHA-256 firmado corresponde al artefacto que atravesó el gate release, sin recompilación intermedia.
- Un fallo previo a publicación conserva la release estable.
- Un defecto posterior genera una versión superior desde el último tag bueno y recorre el pipeline completo.
- SQLite, descargas y la última versión verificada de yt-dlp sobreviven a los escenarios de recuperación declarados.

## Límites

- SignPath Foundation decide la admisión y puede exigir ajustes adicionales.
- La firma válida no garantiza ausencia inmediata de avisos SmartScreen; la reputación se construye con distribución legítima.
- YouTube y otros proveedores externos pueden cambiar; la evidencia prueba el comportamiento observado, no disponibilidad futura.
