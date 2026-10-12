# Verificación de streaming y listas — 2026-10-12

La rama contiene implementación de US-067–US-072, además del plan inicial `f678cf2ce78e280b75001ca48ad0009c8596cdb0`. Este informe distingue pruebas de código, proveedores reales y paquete ejecutado. Las historias siguen `partial`, el ledger `open` y la aceptación manual `pending`; no se certifica una release.

## Última revisión: precisión y final redondeado

El gate `quality-pr-rounded-final.log` aprobó la última fuente el 2026-10-12, 07:21:31–07:23:32 UTC: **345 pruebas Python**, **17 suites / 237 pruebas JavaScript**, contrato, integridad Python, lint, build y auditoría npm con cero vulnerabilidades notificadas. Permanecen 39 avisos de deprecación Python. Fingerprint del gate: `F6481AEF6FE9B73001D8C76CB4C67C77F07DAB33BD91EFC8BC7C76946BF4F13E`; fingerprint de implementación: `2ecd042763072ecb1fa7f20bd361ba0bb5e30baab8877371c79ef7bb815c1698`. El gate declara `commit: null`: se probó un árbol modificado y no se inventa un SHA previo al commit.

Se conserva el backend empaquetado ya construido (su fuente no cambió) y se empaqueta el renderer compilado por este gate con `node node_modules/electron-builder/cli.js --win --x64 --dir --publish never`, desde `electron`. Esto produce un candidato `win-unpacked` para comprobación real; el instalador NSIS anterior no contiene este último ajuste y no se publica ni se declara actualizado.

SHA-256 del candidato final `win-unpacked`:

| Archivo | SHA-256 |
|---|---|
| `Dr. Download.exe` | `25757c2b661fb5393d3908c8130c3bf7e190edc786450aae62857e46b6ed8340` |
| `resources/app.asar` | `1304da94c1f0576bcef204935b31b0e9be8919d17043c9cf0f1f8f938f34b9a1` |
| `resources/backend/dr-download-backend.exe` | `394b000a46b1dd8d788e014fa90f55cb9758bae513d0e7f262983d03a0f78ac5` |

`real-packaged-rounded-v4` (07:24:22–07:25:57 UTC) conserva resultado global **failed**: al iniciar la lista, YouTube rechazó el vídeo o audio y la UI mostró denegación de acceso. Antes del rechazo pasaron CRUD real, navegación, pausa/silencio, ambas búsquedas pausadas y 15 s continuos por proveedor, sin eventos waiting/stalled/error durante la observación:

| Fuente | Primer fotograma | Búsqueda en reproducción | Posición pausada solicitada / observada |
|---|---:|---:|---:|
| YouTube 1080p | 7,813 s | 3,392 s | 20,50 / 20,48 s |
| Vimeo 720p | 6,222 s | 1,304 s | 20,50 / 20,52 s |

Estos tiempos pasan los umbrales en esta ejecución; no anulan los incumplimientos anteriores ni acreditan estabilidad universal. El recorrido no llegó al avance natural ni al reinicio automático por el fallo del proveedor. Cerró normalmente, sin limpieza forzada y sin procesos propios residuales. Los diez minutos continuos pertenecen al candidato anterior identificado más abajo; no se atribuyen al binario final. La comprobación manual completa de avance natural del candidato final sigue pendiente, aunque la regresión del redondeo pasa en Jest.

La comprobación independiente `restart-proof-v2` pasó entre 07:29:02 y 07:29:24 UTC. Reutilizó el helper de procesos del launcher y la fase existente `--verify-persistence` del script CDP sobre el **mismo perfil SQLite** de la ejecución fallida, sin sustituir su contenido. Tras reiniciar el ejecutable real, la lista y sus ítems coincidieron exactamente; fuentes y runtimes conservaron sus hashes, cierre normal, cero procesos propios residuales. Su alcance es persistencia y reinicio, no reproducción ni avance automático. La primera preparación de este chequeo apuntó a una ruta de script inexistente, requirió limpieza del proceso propio y no ejecutó la prueba; se conserva como `restart-proof` y no se atribuye ese error del harness a la aplicación.

Hashes de evidencia local final (los archivos brutos permanecen excluidos de Git):

| Archivo relativo a `artifacts/quality/streaming-implementation/` | SHA-256 |
|---|---|
| `quality-pr-rounded-final.log` | `e09edabd6ecb2d3137b0f34c91b086abc76c8b95569c75a239a2384d5626595d` |
| `real-packaged-rounded-v4/evidence.json` | `b27b39b73d8d1d64728469f60ba2f5dfd486ff7be14bc93efb204a7ba710af96` |
| `real-packaged-rounded-v4/restart-proof-v2/persistence-evidence.json` | `1d6b9d5cb7f3dfb3fe8b9cec368b55ddaa246e9f4947c2f51a75ec3ab0465636` |
| `verify-current-persistence.ps1` (chequeo independiente, no código del producto) | `16fe2f9adb120dfe11c1b4023dec46f1ea329eb5b500720256f91f0cd147cef8` |

## Revisión de precisión, anterior al ajuste por duración redondeada

Tras detectar el exceso de 0,24 s en la búsqueda pausada de Vimeo, la UI mantiene la decodificación oculta y silenciada, pero reduce de 4× a 1× durante el último medio segundo. No utiliza una búsqueda por bytes ni cambia de formato o proveedor. El backend y su contrato no cambian en esta revisión.

El gate completo `quality-pr-precision-final.log` pasó el 2026-10-12, 07:11:33–07:13:24 UTC: **345 pruebas Python**, **17 suites / 236 pruebas JavaScript**, contrato, integridad Python, lint y build; auditoría npm con cero vulnerabilidades notificadas y 39 avisos de deprecación Python. El fingerprint del gate es `5B3625F80056CD60E7B94B5C7CA6EB9ED0472D2D6E5E69F3CE9F0AE081530518`; `quality-pr.json` registra `commit: null`, por lo que se identifica mediante ese fingerprint y no se le atribuye un commit inexistente en el momento de probar. Fingerprint de implementación bajo `backend`, `electron` y `tools`: `785ec452a537e80f2f8419ddca9a262555af515a99429aceb4322ae3f64da19a`. Los resultados anteriores se presentan con su propia identidad y sus fallos conservados.

`package-win-precision-final.log` registra una construcción Windows completa con salida cero. Este candidato unsigned tiene identidades nuevas:

| Archivo | SHA-256 |
|---|---|
| `Dr-Download-Setup-2.1.0-x64.exe` | `f24df0e1daef59d6a895d88b02203ef1b31e93be1955ef28818229e8a7b4c834` |
| `resources/app.asar` | `b433afeb3c8255696ee8caacb2b5298ed85b16207a69594a0b24242493454414` |
| `resources/backend/dr-download-backend.exe` | `394b000a46b1dd8d788e014fa90f55cb9758bae513d0e7f262983d03a0f78ac5` |

`real-packaged-precision-v3` (07:17:58–07:19:49 UTC) pasó ambas búsquedas pausadas a 20,50 s: YouTube 20,49 s, Vimeo 20,52 s. Inicio: 6,620 s y 6,637 s; búsqueda en reproducción: **6,957 s, falla** y 1,577 s. Pasaron 15 s continuos por fuente sin eventos de interrupción, CRUD y anterior/siguiente. Falló el avance natural: YouTube declaraba 635 s enteros, mientras el elemento terminó en 634,618 s. La UI rechazaba ese fin por una tolerancia fija de 0,25 s.

La regresión `a backend-confirmed natural end tolerates provider duration rounded to whole seconds` reproduce ese rechazo; `rounded-duration-red.log` lo conserva y `rounded-duration-green.log` registra 25 pruebas React aprobadas tras corregirlo. La UI admite hasta un segundo para metadatos de duración entera y conserva 0,25 s para duración fraccionaria; siempre exige backend `ended` sin error. No se reduce la precisión de la búsqueda ni se modifica la validación de recuperación de transporte. El paquete de esta tabla precede a esa corrección: su NSIS no se presenta como binario de la última revisión.

## Candidato anterior, corregido tras la carrera de búsqueda

El stream privado lleva una revisión creciente. Una revisión inferior se rechaza antes de tocar el proceso actual, y un EOF prematuro o sin backend `ended` falla sin avanzar la lista. Las regresiones `test_late_browser_retry_cannot_reserve_an_older_source_or_kill_current_process` y `an early end without a backend error cannot advance a playlist` fallaron antes del cambio y pasaron después. La suite focalizada aprobó 70 pruebas Python y 62 JavaScript; esos conteos no sustituyen el gate completo.

El smoke `real-api-revision-final` pasó reproducción de ambos proveedores desde cero y 15,23 s, rechazo 409 de una revisión anterior sobre HTTP real, CRUD SQLite e importación de 29 entradas. No se usó una respuesta simulada para ese 409. Fingerprint de implementación: `9d21ed7831068e51bc3868a6ebaf2bc61ad0efa65e2ada03528e16531bfb1776`, calculado con el mismo algoritmo descrito más abajo.

El gate completo posterior a la corrección terminó aprobado el 2026-10-12, 06:52:29–06:54:41 UTC: **345 pruebas Python**, **17 suites / 235 pruebas JavaScript**, contrato, integridad Python, lint y build aprobados; auditoría npm con cero vulnerabilidades notificadas. Conservó 39 avisos de deprecación. `quality-pr-revision-final.log` y `artifacts/quality/quality-pr.json` identifican el árbol probado; el informe se completa después, sin modificar el código probado. El fingerprint de workspace de esa ejecución fue `C147314E3116B4B2C62E0B2E1647F6E1A4E2F5896E685DFE0CB51A5CDE26F7FE`; difiere del fingerprint de implementación porque también incluye documentación y otros archivos del gate.

SHA-256 del candidato corregido, distinto del candidato inicial:

| Archivo | SHA-256 |
|---|---|
| `Dr-Download-Setup-2.1.0-x64.exe` | `8cfdffb3b5f5350b52156c96d587d3a0f1853399e0372f4f76805f08c98815bd` |
| `resources/app.asar` | `c30d4abda1297d840b08ad26438998088b37cd64e7c41c9d586ac235a5a47658` |
| `resources/backend/dr-download-backend.exe` | `60290e1868dd38d7ee54aef33c94287da6739d7a3fc5d2c607aa801c18251e7c` |

Los resultados del candidato inicial que siguen no se atribuyen a estos binarios nuevos.

## GUI del candidato con protección de revisión, anterior al ajuste de precisión

`real-packaged-600-v2`, ejecutado entre 06:49:38 y 07:01:13 UTC, conserva resultado **failed**. Sobre los hashes corregidos anteriores pasó reproducción directa, pausa, silencio, búsqueda decimal en pausa, navegación, CRUD de listas y la observación continua:

| Fuente | Primer fotograma (límite 8 s) | Búsqueda (límite 5 s) | Observación | waiting/stalled/error |
|---|---:|---:|---:|---:|
| YouTube 1080p | **8,300 s: falla** | **6,225 s: falla** | 600 s | 0 |
| Vimeo 720p | 7,018 s: pasa | 1,690 s: pasa | 15 s | 0 |

YouTube registró 30.444 fotogramas totales y 312 descartados; Vimeo, 380 y 6. Después, al volver a resolver YouTube para reproducir la lista, el proveedor denegó el acceso y la UI mostró la causa. Por ello esta ejecución no acredita anterior/siguiente, avance natural ni reinicio del candidato corregido. El fallo no se convierte en éxito por haber pasado reproducción directa. La aplicación cerró normalmente, sin limpieza forzada ni procesos propios residuales. El manifiesto conserva hashes previos; el launcher no alcanzó la comprobación posterior porque falló el recorrido funcional.

Un diagnóstico posterior comparó cuatro aperturas alternas de formatos HLS/HTTPS disponibles para el mismo vídeo y offset; solo midió el primer bloque MP4 (1.290–1.306 bytes), entre 0,713 y 1,753 s. No demuestra mejora del primer fotograma ni explica el 403; no se cambió la selección de formato basándose en ese dato.

La repetición `real-packaged-short-v2` (07:08:53–07:09:55 UTC) volvió a fallar: el inicio de YouTube fue 5,664 s y el de Vimeo 5,152 s, pero la búsqueda en pausa de Vimeo terminó en 20,74 s frente a 20,50 s solicitados. El descarte a 4× podía sobrepasar la tolerancia de 0,2 s bajo variación de entrega de fotogramas. Se conservó el fallo, se añadió una regresión roja y se redujo la aproximación a 1× durante el último medio segundo. `seek-precision-red.log` muestra el fallo antes del cambio; `seek-precision-green.log`, 24 pruebas React aprobadas después. La revisión de binarios y fuentes de las ejecuciones anteriores no se atribuye a este último cambio.

## Gate inicial, anterior a la protección de revisión

`npm run quality:pr` terminó correctamente el 2026-10-12, 06:24:29–06:26:48 UTC, en Windows 10 x64, compilación 19045:

- 339 pruebas Python aprobadas; 39 avisos de deprecación de dependencias, sin fallos.
- 17 suites JavaScript, 230 pruebas aprobadas.
- Validador contractual, integridad de dependencias Python, ESLint y compilación Vite aprobados.
- `npm audit --prefix electron --audit-level=moderate`: cero vulnerabilidades notificadas, incluyendo dependencias de desarrollo.

Se probó un árbol modificado basado en `f678cf2`; no se atribuyen esos cambios al commit padre. Fingerprint de los archivos de implementación y pruebas bajo `backend`, `electron` y `tools`: `5585cd6a8a217d7f94b72544af0075c1e5a5e85d8d635e5c3cbf01dfab7a31f1`. Se calcula con `git ls-files --cached --others --exclude-standard -- backend electron tools`, SHA-256 de los bytes de cada archivo existente y SHA-256 del diccionario JSON con claves ordenadas. Excluye documentación y artefactos ignorados; el manifiesto completo está en la evidencia gráfica. La documentación del informe se completa después del gate y requiere su propia validación contractual.

## Backend y proveedores reales

`tools/smoke_test_playback.py --artifact-dir artifacts/quality/streaming-implementation/real-api-final --playlist-url https://www.youtube.com/playlist?list=PLBB231211A4F62143` pasó con Python, backend, yt-dlp, Node, FFmpeg/FFprobe reales y SQLite aislado, sin dobles de proveedores.

| Fuente pública | Vídeo/audio confirmados | Inicio solicitado | Primer byte del stream | Bytes examinados |
|---|---|---:|---:|---:|
| YouTube `aqz-KE-bpKQ` | 1080p H.264 + AAC | 0 s | 4,302 s | 2.107.566 |
| YouTube `aqz-KE-bpKQ` | 1080p H.264 + AAC | 15,23 s | 2,159 s | 2.111.239 |
| Vimeo `1084537` | 720p H.264 + AAC | 0 s | 0,408 s | 2.118.662 |
| Vimeo `1084537` | 720p H.264 + AAC | 15,23 s | 0,956 s | 2.107.186 |

La resolución previa tardó 9,467 s en YouTube y 6,517 s en Vimeo. Primer byte no significa primer fotograma ni satisface el umbral total de ocho segundos. FFprobe confirmó ambas pistas en los cuatro fragmentos; la lista real de YouTube importó 29 entradas y el CRUD persistió en SQLite. No se ensayó una lista real de 500 entradas ni una importación real de Vimeo.

## Identidad del candidato Windows inicial

`npm --prefix electron run package:win` creó un candidato unsigned. El smoke ejecuta `win-unpacked`, sin instalar NSIS en el perfil habitual. SHA-256:

| Archivo | SHA-256 |
|---|---|
| `Dr-Download-Setup-2.1.0-x64.exe` | `63f02aefb42c304df90db2299ea0610d0169e2059423256acbc7e9abf582f4bd` |
| `resources/app.asar` | `af8f4b1f3ce5e237e592e299e6da81c35666ffaaad818436c32864e164b35759` |
| `resources/backend/dr-download-backend.exe` | `da60c50ebf03f1426fd78a1de28e2e242e6a6bab115708f7dd0ffb80127f3c59` |
| Motor real provisionado `yt-dlp.exe` 2026.08.19 | `66674953fe251b89f4d08c5f0e35e0728679bd67ab3d7d05c0562af101dd3e7a` |

El motor se contrastó con `SHA2-256SUMS` de la release oficial y se copió explícitamente al perfil aislado. Esto permite verificar reproducción con un motor real conocido; no acredita su descarga inicial. El manifiesto gráfico registra también los hashes de Node, FFmpeg/FFprobe, ejecutable y fuentes, y comprueba que no cambien durante la ejecución.

## GUI del candidato inicial: funciones aprobadas, latencias fallidas

La ejecución `real-packaged-600-v1` completó el recorrido funcional, pero su resultado global es **failed** por tres umbrales de tiempo. No se convierte en aprobación de aceptación:

| Fuente | Primer fotograma (límite 8 s) | Búsqueda a 15,23 s (límite 5 s) | Observación continua | Eventos waiting/stalled/error durante observación |
|---|---:|---:|---:|---:|
| YouTube 1080p | **12,353 s: falla** | **8,339 s: falla** | 600 s | 0 |
| Vimeo 720p | **8,661 s: falla** | 1,188 s: pasa | 15 s | 0 |

Pasaron decodificación real, pausa, silencio, búsqueda decimal en pausa con error inferior a 0,2 s, navegación sin reiniciar el medio, creación/duplicado/renombrado/eliminación de entradas, anterior/siguiente, avance natural y detención al final de la lista. El renderer solo pidió recursos de la aplicación y `dr-stream:`; no cargó reproductores ni scripts del proveedor. La observación de YouTube registró 31.134 fotogramas totales y 251 descartados; Vimeo, 383 y 7. Cero eventos de interrupción no significa cero fotogramas descartados.

La aplicación cerró sin limpieza forzada del helper y sin procesos propios residuales. La prueba larga no inició su fase de reinicio porque los umbrales fallaron. El smoke API se ejecutó en paralelo durante parte del comienzo; no se atribuye causalidad a esa concurrencia ni se presenta como benchmark aislado de red. Se conserva `status: failed` junto a `functional_status: passed` y todos los tiempos, sin ocultar los fallos.

Comando ejecutado:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File electron/scripts/run-playback-ui-smoke.ps1 -Packaged -Duration 600 -EnginePath artifacts/quality/streaming-implementation/real-api/data/engine/yt-dlp.exe -ArtifactDirectory artifacts/quality/streaming-implementation/real-packaged-600-v1
```

La ejecución corta posterior `real-packaged-short-v1` detectó una petición del offset anterior después de otra búsqueda y un fin prematuro sin error backend. La revisión inicial del paquete no es suficiente para acreditar esa carrera. Se conserva ese fallo y se añade una revisión monotónica del origen y validación del EOF antes de repetir sobre un candidato nuevo.

## Fallos conservados y correcciones verificadas

- La búsqueda nativa de Chromium reiniciaba el stream y perdía el offset decimal. Ahora FFmpeg confirma el tiempo del primer paquete y React decodifica el tramo inicial oculto y silenciado, hasta un fotograma solicitado confirmado. Se conserva la pausa y se descartan respuestas de sesiones antiguas.
- Los GOP largos retrasaban la entrega: la prueba con FFmpeg real exige un fragmento antes de tres segundos y el remux fragmenta cada segundo.
- Un EOF con código cero podía corresponder a contenido truncado. Se retienen errores acotados y se exige duración completa de ambas pistas antes de considerar recuperado un error de transporte. Un servidor HTTP real que corta la conexión entregaba 39/150 fotogramas antes del cambio; con reconexión limitada al mismo origen entrega 150/150. Si continúa fallando, la prueba exige error visible y término acotado.
- Se observaron denegaciones 403 reales de YouTube, DRM `skd://` en otra muestra de Vimeo y cortes TLS. Permanecen fallos explícitos; no se cambian clientes, fuentes ni formatos para ocultarlos. La muestra pública de Vimeo usada en la verificación no tiene ese DRM.
- El arranque sin motor preparado falló durante una transferencia grande con `DECRYPTION_FAILED_OR_BAD_RECORD_MAC`. No se diagnosticó como fallo de confianza de certificados ni se desactivó TLS. Se conserva esa ejecución separada de las ejecuciones provisionadas.
- El spike real `--sponsorblock-mark all` devolvió un capítulo; no se afirma que esa opción del motor falle. La consulta primaria separada con `httpx` permite comprobar consentimiento vigente, categorías y timeout de cinco segundos. No se acredita salto/deshacer con un segmento externo real en la GUI.

La medición gráfica de búsqueda usa el primer fotograma decodificado correspondiente al destino y el instante en que la UI vuelve a mostrarlo; no usa un fotograma posterior tomado después de consultar el estado por IPC. Los límites de ocho y cinco segundos siguen siendo condiciones de fallo del script. Los intentos anteriores se conservan, incluidos inicios de 8,377 y 12,884 s y búsquedas que excedieron cinco segundos; una ejecución posterior favorable no demuestra latencia garantizada.

## Evidencia y límites

Los logs, JSON, capturas, perfiles temporales y binarios se conservan localmente en `artifacts/quality/streaming-implementation/`, excluido de Git. Este informe versionado no presume que esos archivos estén disponibles en otro equipo. Los comandos y el [inventario ejecutable](streaming-validation.md) permiten repetir las comprobaciones con nuevas identidades.

La ausencia de reproductor, iframe y scripts oficiales evita sus peticiones publicitarias. No garantiza eliminar publicidad incorporada al medio ni cobertura universal de SponsorBlock. Los proveedores pueden caducar URLs, exigir sesión o rechazar acceso. Faltan la matriz completa Windows 10/11 limpio, instalación/desinstalación, escalas/idiomas/teclado/pantalla completa, codecs alternativos, consentimiento/revocación con sesiones reales, SponsorBlock real e importación de 500 entradas. La banda de red no se calibró como benchmark de 50 Mb/s. Firma y publicación siguen bloqueadas por los gates de release; subir una rama no publica un instalador ni integra `main`.
