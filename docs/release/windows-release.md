# Publicación Windows

## Estado de implementación

Esta guía define **contratos objetivo**. El workflow PR construye el NSIS y un job nuevo instala ese artifact-id, ejecuta el smoke real con runtimes incluidos y lo desinstala. `quality-release` separa el gate unsigned, la solicitud real a SignPath, la validación de firma y otra instalación post-firma. La existencia de estos pasos no acredita su ejecución, aprobación ni la matriz Windows 10/11. Ningún PASS de otro SHA se atribuye al candidato actual.

## Contrato objetivo de build interno

```powershell
python -m pip install -r backend/requirements-build.txt
npm ci --prefix electron
npm run package:win --prefix electron
```

El pipeline obtiene FFmpeg/FFprobe del build original fijado, verifica los hashes registrados en `THIRD_PARTY_NOTICES.md`, compila React, empaqueta FastAPI con PyInstaller y crea un NSIS x64 por usuario. Una copia local con hash diferente bloquea el build. La desinstalación debe conservar preferencias e historial.

El usuario instala y abre la aplicación directamente en Windows. No necesita VM, Docker, Python ni Node externos. «Windows limpio» describe el entorno de aceptación: un equipo físico o una VM Windows 10/11 sin herramientas de desarrollo ni runtimes externos. La VM permite repetir instalación/desinstalación sin alterar una instalación habitual; ejecutar `win-unpacked` en el equipo de desarrollo no demuestra por sí solo este criterio. El primer arranque sin motor verificado requiere conexión para obtenerlo y comprobar su hash.

## Puertas de publicación

- `QA-GATE-RELEASE-UNSIGNED-001`: GitHub Actions construye un único NSIS x64 y registra artifact-id, commit y SHA-256 unsigned. El contrato objetivo `tools/quality-gate.ps1 -Level release` debe probar ese artefacto, finalizar con código 0 y registrar `publishable: false`.
- `QA-GATE-SIGN-001`: el mismo artifact-id se envía a SignPath con aprobación humana. Solo después de recibir el artefacto firmado, el gate post-SignPath objetivo valida SHA-256 signed, Authenticode `Valid`, timestamp válido y publisher `SignPath Foundation`.
- FFmpeg/FFprobe x64 incluidos, sus hashes archivados y licencias reflejadas en `THIRD_PARTY_NOTICES.md`.
- Repositorio de GitHub Releases configurado mediante `DR_DOWNLOAD_UPDATE_OWNER` y `DR_DOWNLOAD_UPDATE_REPO`.
- Instalación, actualización, roll-forward y desinstalación del NSIS exacto probadas en Windows 10/11 limpios.
- Descarga real autorizada de audio y video; archivos reproducibles y logs sin secretos.
- Todas las historias del alcance vigente, derivadas de las fichas y coincidentes con ambas matrices, deben estar `accepted` con evidencia real; alternativamente, producto debe aprobar una reducción de scope.

Nunca se publica un instalador sin firmar. Un build interno o una ejecución sin SignPath completa debe registrar `publishable: false`.

El workflow `quality-release` construye, solicita firma y conserva candidatos/evidencia; no publica una Release automáticamente. `QA-GATE-PUBLISH-001` exige una acción posterior del `release approver` que publique únicamente el SHA-256 firmado validado, sin recompilar ni reemplazar assets bajo el mismo tag.

## Prueba sin VM local

La restricción de recursos del mantenedor se atiende con runners Windows estándar alojados por GitHub. En PR, `installed-windows` recibe exclusivamente el instalador del job de build; no configura Python ni Node. `tools/test-installed-windows.ps1` rechaza ejecución en el equipo de desarrollo, instalaciones/perfiles existentes y hashes diferentes; reduce `PATH` a Windows antes de instalar. El smoke se conduce con `resources/node/node.exe`, usa el backend/FFmpeg incluidos y comprueba UI ES/EN, IPC y tres descargas reales. Después compara hashes de `config.json`, `downloads.db` y descargas, y verifica eliminación de binarios, runtimes, accesos y registro. Los procesos del smoke se cierran antes de desinstalar.

La evidencia `artifacts/quality/installed/evidence.json` registra SO real, imagen, SHA, run, artifact-id, tiempos y códigos de salida. El runner lleva herramientas preinstaladas fuera del `PATH` y usa Windows Server: **no equivale a Windows 10/11 sin runtimes instalados**. Por ello `clean_windows_10_11_verified` y `publishable` permanecen `false`; esta prueba aporta cobertura del instalador sin ocupar una VM en el PC del mantenedor. La matriz de consumo, actualización y roll-forward sigue pendiente. Un fallo de red/YouTube se conserva como fallo, sin simulaciones.

Incluso si falla la inspección o descarga externa, se ejecuta la desinstalación y se comparan los archivos de usuario que realmente existan. `uninstall_verified` y `user_data_preserved` registran ese resultado parcial; `status: failed` e `installer_lifecycle_verified: false` mantienen bloqueado el gate completo. Los hitos `startup-result.json`/`settings-result.json` y `failure-ui.txt`/`failure.png` permiten identificar hasta dónde llegó la UI real y qué error mostró.

## Configurar firma sin comprar certificado

[SignPath Foundation ofrece firma gratuita para proyectos OSS](https://signpath.org/), sujeta a [sus condiciones y aprobación](https://signpath.org/terms.html). No hay garantía de admisión ni certificado disponible por añadir un workflow. La solicitud corresponde al titular del repositorio; no enviar tokens por chat.

1. Solicitar admisión en [SignPath](https://signpath.org/apply.html), declarar repositorio, licencia MIT, componentes y roles reales de revisión/aprobación.
2. Instalar su GitHub App y vincular el proyecto al origen GitHub alojado por GitHub. Configurar una política de producción con aprobación humana y certificado Foundation. El artifact configuration debe aceptar el ZIP generado por `upload-artifact`, restringir el NSIS `Dr-Download-Setup-*-x64.exe` y sus metadatos de producto/versión; no firmar binarios de terceros con la identidad del proyecto. Ver [integración oficial](https://docs.signpath.io/trusted-build-systems/github).
3. Configurar `production-release` con revisores humanos requeridos. Añadir variables `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_SIGNING_POLICY_SLUG` y el secreto `SIGNPATH_API_TOKEN` mediante la configuración segura de GitHub.
4. Tras integrar el workflow por PR, ejecutar `quality-release` sobre el commit revisado. El mismo artifact-id unsigned se envía a SignPath; el retorno se valida por ruta explícita, Authenticode `Valid`, publisher, timestamp/cadena, hash y metadatos de origen. Otro job prueba el instalador firmado exacto, sin reconstruirlo.

Mientras falten cuenta aprobada, configuración o aprobación humana, la firma sigue bloqueada. No se usa una firma autofirmada para aparentar un editor confiable, ni se publican candidatos unsigned.

## Evidencia por etapa

| Etapa | Responsable | Evidencia | Bloqueo |
| --- | --- | --- | --- |
| Build único | `author` | commit, tag, run, artifact-id y SHA-256 unsigned | Identidad ausente o más de un build candidato |
| Gate unsigned previo a firma | `reviewer` | instalación, inicio, streams, procesos, datos, desinstalación, SHA-256 unsigned y `publishable: false` | Se prueba `win-unpacked`, otro archivo, falta un resultado o se intenta verificar firma |
| Firma SignPath | `release approver` | solicitud, aprobación y artifact-id | SignPath no devuelve el artefacto firmado o cambia su origen |
| Gate post-SignPath | `reviewer` | SHA-256 signed, instalación, inicio, desinstalación, publisher, timestamp y Authenticode `Valid` | Firma no `Valid`, configuración ausente, publisher distinto o prueba incompleta |
| Publicación | `release approver` | aprobación final, tag y hash del asset | Hash distinto, evidencia incompleta o gate abierto |

Cada etapa consume la identidad emitida por la anterior. Una discrepancia invalida el candidato completo.

## Recuperación

La aplicación no se reinicia con descargas activas. Si una actualización falla, el reemplazo no se promueve y permanece la última versión previamente verificada. Si no existe una versión verificada de yt-dlp, la descarga queda bloqueada con error accionable.

Un defecto de aplicación ya publicado activa `QA-GATE-ROLLFORWARD-001` y `docs/operations/rollback-runbook.md`: se congela el canal, se parte del último tag bueno, se crea un parche superior y se repite el pipeline completo con un artefacto nuevo y firmado antes de reabrir el canal.

## Gate específico de carpetas

Antes de publicar, probar una carpeta nueva, una ruta relativa, un archivo usado como carpeta, una carpeta sin permisos y un volumen con poco espacio. La UI debe mostrar `error_code`, causa y recuperación; nunca publicar el error técnico sin traducir.

La ampliación aprobada US-062–US-066 añade espacio estimado estricto API/IPC, compatible MP4 H.264/AAC sin sustitución, conectividad y operaciones veraces, borrador de sesión, guardado/consentimiento, recuperación ES/EN y búsqueda/filtro/repetición protegida. Sus nuevos MAN-US-062–MAN-US-066 permanecen pending; no se excluyen del universo de release ni se aceptan por documentación o Jest aislado.
