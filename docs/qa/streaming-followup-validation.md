# Revalidación de streaming y listas — 2026-10-12

Esta revisión continúa los fallos documentados en [la validación anterior](streaming-implementation-validation.md). Conserva aquella evidencia y distingue correcciones de código, ejecución real del paquete y aceptación de release. US-067–US-072 siguen `partial`; no se presume cumplida la matriz Windows 10/11.

## Diagnóstico y correcciones

- La comparación real de vídeo HLS 312 y HTTPS 299 no justificó cambiar al segundo: ambos podían fallar en la misma resolución y HLS fue más rápido en las búsquedas observadas. En una resolución denegada, vídeo 312 funcionó por separado y audio HTTPS 140 recibió 403. En otra, los audios HTTPS 139/140/249/250/251, incluidas variantes DRC, recibieron 403; HLS 233/234 funcionó. Evidencia: `protocol-*-comparison.json`, `denial-tracks.json`, `denial-audios.json`.
- La selección primaria ahora prefiere audio HLS para vídeo HLS dentro del códec preferido, conservando AAC antes que Opus. FFprobe verifica el audio HLS con códec desconocido antes de registrar la sesión. Un fallo de esa verificación detiene; no activa otro cliente, audio ni formato. Ocho resoluciones reales independientes abrieron 312+234, pero ese chequeo de apertura no acreditaba decodificación completa.
- La GUI detectó que ese audio necesitaba `aac_adtstoasc` al copiarlo a MP4 fragmentado. Una regresión local con HLS/ADTS real reprodujo el mismo fallo con FFmpeg incluido antes de corregirlo. Se aplica el filtro solamente a AAC, conservando `-c copy`; convierte cabeceras sin recodificar, como describe [FFmpeg](https://ffmpeg.org/ffmpeg-bitstream-filters.html#aac_005fadtstoasc).
- La lista omite con aviso un elemento que falla durante su carga inicial, conservando la dirección solicitada. Un fallo después de empezar o durante una búsqueda sigue deteniendo la reproducción con error visible. Las regresiones React comprueban los tres casos y el aislamiento de respuestas antiguas.

## Una prueba que podía aprobar incorrectamente

`real-api-hls-pair/evidence.json` declaró `passed` aunque la primera muestra de YouTube contenía solo 2185 bytes y la sesión estaba `failed`. **Ese resultado queda invalidado como prueba de reproducción.** El smoke anterior comprobaba cabeceras de ambas pistas; eso no demostraba su decodificación.

El smoke ahora exige ausencia de error de sesión y al menos dos fotogramas decodificados por pista, con marcas finitas y un tramo de al menos 0,25 s. `real-api-aac-red` rechaza correctamente el fragmento defectuoso. Otra ejecución detectó que 2 MiB podían cortar el fragmento antes del audio: la medición a 15,23 s encontró 127 fotogramas de vídeo y uno de audio a 2 MiB, frente a 321/130 a 4 MiB y 978/611 a 8 MiB. Se amplió la captura a 8 MiB conservando las aserciones; no se convirtió el resultado fallido en aprobado.

`real-api-aac-complete` pasó con yt-dlp 2026.08.19 y las herramientas incluidas, sin cookies: YouTube H.264/AAC 1080p y Vimeo H.264/AAC 720p, desde cero y desde 15,23 s. Se decodificaron 945/656 y 978/611 fotogramas vídeo/audio de YouTube; 583/1122 y 577/1125 de Vimeo. Pasaron las revisiones obsoletas rechazadas por HTTP, CRUD SQLite e importación real de 29 elementos. Su fingerprint de fuente es `10b117681a361d93671b11348bc8d0f4cba17973af28e01bf270bd9d766ed1f3`; acredita backend real, no GUI instalada.

## Gate y candidato Windows

`npm run quality:pr` terminó con código 0 el 2026-10-12, 15:55:53–15:57:45 UTC, después del ajuste del launcher: **355 pruebas Python, 17 suites / 241 pruebas JavaScript**, contrato, integridad Python, lint y build aprobados; auditoría npm sin vulnerabilidades notificadas. Permanecen 39 avisos de deprecación Python. `quality-pr-followup-complete.json` identifica el árbol probado como `74983D0AC8DB205FB3FEB2934204FC9AA06F92630285B32AEA6A40CC1677898F`, `commit: null`, `publishable: false`; se probó código sin commit y no se le atribuye un SHA ficticio. Las adiciones posteriores a este informe no cambian el código probado. El gate anterior al ajuste, `quality-pr-final`, pasó con 355/240 pruebas y conserva su identidad aparte.

`npm --prefix electron run package:win` terminó con código 0, produciendo el NSIS y su `win-unpacked` correspondiente, sin firma configurada. SHA-256:

| Archivo | SHA-256 |
|---|---|
| `Dr-Download-Setup-2.1.0-x64.exe` | `698694a2f7de220a6e34ed89895fc068290079765a2818033e72b3c153e02ccd` |
| `win-unpacked/Dr. Download.exe` | `7490df80cd6904c532be903bccca8dd5974261755b1cb8bcc3e8f087b883e1a3` |
| `resources/app.asar` | `5c6ed49680786ab5b1a68cf1e9cadd5758ba5f0ae020232955d56b73c5c93970` |
| `resources/backend/dr-download-backend.exe` | `1435818747d219d148d85572315f7311a32fdd743c8d3ed0f4538fac87e570a7` |

`real-packaged-aac-short` completó el recorrido funcional, incluido avance natural, fin de lista, reinicio y persistencia SQLite. El avance se comprobó buscando a 0,5 s del final de cada vídeo y dejando terminar el medio real. Pasaron pausa, silencio, búsquedas decimales y 15 s continuos por proveedor. Ambas ejecuciones cerraron normalmente, sin limpieza forzada ni procesos propios residuales; fuentes, paquete y runtimes conservaron sus hashes.

| Fuente | Primer fotograma | Búsqueda decodificada |
|---|---:|---:|
| YouTube 1080p | **9,275 s: falla ≤ 8 s** | 2,761 s |
| Vimeo 720p | 4,825 s | 1,168 s |

El resultado global permanece **failed**, aunque `functional_status` sea `passed`. La resolución de YouTube ocupó aproximadamente 6,576 s y la entrega hasta el fotograma otros 2,699 s. La comparación diagnóstica con análisis FFmpeg limitado a 1 s / 1 MiB no produjo una mejora consistente; no se incorporó ese ajuste. Las tres inspecciones del proveedor midieron 3,800–5,794 s, más 0,623–0,774 s de verificación de audio. No se afirma haber resuelto una garantía de latencia por repetir hasta conseguir un tiempo favorable.

La primera ejecución larga `real-packaged-aac-600` fue interrumpida por un error del harness: su deadline permitía `600 + 450 = 1050 s`, insuficiente para dos tramos de 600 s y las operaciones de UI. No produjo evidencia final aprobada y requirió cierre forzado; no acredita la prueba de diez minutos por ambos proveedores. La regresión evalúa la expresión real de PowerShell y falla con 1050 s; corregida a `2 * Duration + 450`, las ocho pruebas del harness pasan. El producto empaquetado conserva sus bytes; esta corrección afecta exclusivamente al launcher y su prueba.

`implementation-manifest.json` compara los 91 archivos bajo `backend`, `electron` y `tools`: solo cambiaron el launcher y su prueba respecto del recorrido corto. Verifica además que los cuatro archivos del candidato de la tabla conservan su SHA-256. El fingerprint después del ajuste de pruebas es `227189006b0a0af443fcabf424dc12c3a51b32b720dd18ff8e151938c1e5849c`; se obtiene del JSON ordenado que mapea cada ruta a su SHA-256 en minúsculas.

## Diez minutos por proveedor sobre el mismo paquete

`real-packaged-aac-600-v2` terminó el 2026-10-12, 15:33:15–15:55:11 UTC, con **resultado global failed** y `functional_status: passed`. Completó 600 observaciones de un segundo por proveedor, ambas búsquedas pausadas, navegación, anterior/siguiente, avance natural, fin de lista y persistencia tras reinicio. Ambas ejecuciones cerraron normalmente, sin limpieza forzada ni procesos propios residuales; el launcher verificó hashes de fuentes y runtimes al terminar.

| Fuente | Primer fotograma | Búsqueda decodificada | Observación continua | Eventos waiting/stalled/error |
|---|---:|---:|---:|---:|
| YouTube 1080p / 60 fps | **8,563 s: falla ≤ 8 s** | 3,050 s | 600 s | 0 |
| Vimeo 360p / 24 fps | 5,900 s | 0,798 s | 600 s | 0 |

Las posiciones pausadas solicitadas a 20,50 s fueron 20,49 y 20,50 s. El tiempo del medio avanzó 607,699 y 607,995 s durante los bucles; la instrumentación añade tiempo al intervalo de pared. Las lecturas independientes de Chromium mostraron bytes de audio y vídeo decodificados en crecimiento, con reproducción activa y sin error.

**Cero eventos de buffering no equivale a cero fotogramas descartados.** Entre las capturas de reanudación y final, YouTube pasó de 144/101 a 36607/2749 fotogramas totales/descartados: 2648 de 36463, aproximadamente **7,26 %**. Vimeo pasó de 11/0 a 14602/1. Se excluyen de esa diferencia los descartes iniciales del tramo oculto de búsqueda, pero el intervalo incluye la navegación breve anterior al bucle. No se ha aislado la causa del descarte en este host ni se acredita fluidez visual completa. La latencia de inicio y la calidad de presentación siguen pendientes; esta ejecución no sustituye la matriz Windows limpia.

## Entorno y límites vigentes

El host real es Windows 10 Home x64, build 19045, con herramientas de desarrollo. No acredita Windows limpio. La inspección del repositorio encontró cero runners propios, cero secretos/variables enumerados y cero entornos de GitHub; no existe evidencia de SignPath configurado ni de aprobación de publicación. Se pidió acceso a Windows 11 limpio y estado de SignPath; sin esos prerrequisitos la matriz y la release continúan pendientes. Los [runners alojados de GitHub](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) Windows x64 usan Windows Server: una prueba allí será complementaria, no aceptación Windows 10/11.

Una descarga de 25 MB desde Cloudflare midió 73,59 Mb/s en 2,718 s, HTTP 200. Es una muestra de capacidad de este host, no una garantía de caudal sostenido de YouTube/Vimeo.

No cargar el reproductor oficial evita sus scripts y peticiones publicitarias; no elimina publicidad ya incorporada al medio. SponsorBlock requiere consentimiento y cobertura comunitaria; el salto/deshacer de un segmento externo real en la GUI sigue pendiente. Tampoco se acreditan por estas pruebas la importación real de 500 entradas, la matriz de idiomas/escalas/accesibilidad ni codecs alternativos.

Los archivos brutos, perfiles y binarios permanecen localmente en `artifacts/quality/streaming-followup/`, excluidos de Git. Los [comandos reproducibles](streaming-validation.md) permiten una nueva ejecución con nueva identidad. Subir la rama no firma ni publica un instalador.

SHA-256 de evidencia local, con rutas relativas a esa carpeta:

| Archivo | SHA-256 |
|---|---|
| `quality-pr-followup-complete.json` | `e1203ab6e4813870a955705bd83f645c27d5c86c2afa0718981e0bceaec8772a` |
| `real-api-aac-complete/evidence.json` | `c427c1e32c5a11efd915601f8f3eca32a88de5f3b88154741ecb2cd2a679710b` |
| `real-packaged-aac-short/evidence.json` | `9877f30f61b9879786560f80a250ed19383202152b67b9f4691aae9fa125a7ec` |
| `real-packaged-aac-600-v2/evidence.json` | `d464188fc609aa92503300a0c754f2a01a07941668eab490dd7f2eae7093d859` |
| `real-packaged-aac-600-v2/identity-and-cleanup.json` | `ed31804fb22aed55eaa2223b33481e9466f2172a7a68d40676b8b85d2db939c7` |
| `real-packaged-aac-600-v2/persistence-evidence.json` | `a1ae8f9ddc740bec064692a1e07040f13e0d700785bb4ca72413ce3f039e88f1` |
