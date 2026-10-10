# Corrección de dependencias npm — 2026-10-09

## Causa y alcance

La auditoría inicial reprodujo 26 alertas moderadas, cero altas/críticas y cero en el árbol declarado de producción. Las 26 son propagaciones del mismo [aviso GHSA-hp3w-g68c-fv3c / CVE-2026-97058](https://github.com/advisories/GHSA-hp3w-g68c-fv3c): `sprintf-js` hasta 1.1.3 permite precisión sin límite y puede lanzar `RangeError`. No había versión corregida publicada al realizar esta revisión.

Dos cadenas de desarrollo introducían el componente:

- Jest/Babel → `@istanbuljs/load-nyc-config@1.1.0` → `js-yaml@3.15.2` → `argparse@1.0.10` → `sprintf-js@1.0.3`.
- electron-builder → `@electron/get@3.1.0` → `global-agent@3.0.0` → `roarr@2.15.4` → `sprintf-js@1.1.3`.

## Corrección y compatibilidad

Los overrides se limitan a esos consumidores: `js-yaml@4.3.2` bajo el cargador de Istanbul y `global-agent@4.1.3` bajo `@electron/get@3`. No se degrada Jest ni electron-builder, no se modifica el paquete vulnerable y no se excluyen alertas del audit.

El cargador de Istanbul llama a `load()`, conservado en la [migración oficial de YAML 3 a 4](https://github.com/nodeca/js-yaml/blob/master/docs/migrate_v3_to_v4.md). Los tipos JavaScript inseguros del esquema antiguo no se restauran. La [versión 4.1 de global-agent](https://github.com/gajus/global-agent/releases) elimina `roarr`; el consumidor usa `bootstrap()` y necesita conservar la conexión por proxy. No se añade una dependencia directa ni cambia el runtime de la aplicación.

`electron/src/__tests__/dependency-compatibility.test.js` comprueba ausencia de `sprintf-js` en el lockfile, carga YAML real con herencia y normalización de opciones, y una petición HTTP real al proxy local mediante `initializeProxy()` del downloader de electron-builder. El proceso separado evita alterar los agentes HTTP del resto de Jest. La prueba de ausencia falló antes del cambio y las otras dos pasaron como referencia previa.

El gate ahora bloquea vulnerabilidades moderadas o superiores en todo el árbol npm. Su prueba contractual falló con el umbral anterior. El lockfile debe verificarse con npm 10, usado por CI, incluyendo peers opcionales; la instalación local no sustituye `npm ci` en Windows limpio.

CI detectó ausencia de `@emnapi/core` y `@emnapi/runtime` 1.11.3 después de que herramientas locales reescribieran el lockfile. Se conservan las resoluciones opcionales del lockfile completo; una prueba adicional comprueba los rangos reales de los peers de `@napi-rs/wasm-runtime` y falló antes de restaurarlas. Ejecutar el gate después del empaquetador permite detectar también una reescritura posterior.

## Evidencia

La auditoría previa está conservada localmente en `artifacts/quality/npm-audit-moderate-before.json`. `npm ci` con npm 10.9.9 completó una instalación nueva con código 0. Las auditorías posteriores de todo el árbol y de producción registran cero vulnerabilidades en `artifacts/quality/npm-audit-moderate-after.json` y `npm-audit-production-after.json`. Las tres pruebas de compatibilidad pasan después de instalar; `npm ls` confirma YAML 4.3.2, global-agent 4.1.3 y ausencia de sprintf-js. No se actualizaron las otras versiones directas ni el runtime Electron.

El commit de código `bb001f640b1aa7dc9539aabc8a6e266d04199dbe` pasó [CI quality-pr](https://github.com/XPERIENCE-LIVE/dr_download/actions/runs/38006908793): `npm ci`, 217 pytest, 97 Jest, contratos, integridad Python, lint, build y audit moderado. El gate local repetido después de empaquetar también pasó, con fingerprint `431AECF8EE722309966266DABEC0E88CFF7AAD3E6B177489E5B9004644A3F4EC` en `artifacts/quality/quality-pr.json`. La prueba adicional de peers explica el incremento a 97 Jest.

Los resultados del [paquete anterior](reliable-workflows-validation.md) permanecen atribuidos a su commit y no certifican este cambio. Cero avisos npm significa cero hallazgos conocidos por esa auditoría en ese momento, no una garantía de ausencia de defectos o una auditoría completa de los binarios incluidos.

## Paquete Windows comprobado

Paquete construido desde `bb001f640b1aa7dc9539aabc8a6e266d04199dbe`, Windows 10 x64, Electron 43.7.9. Smoke real del 2026-10-10, 00:00:41–00:04:08 UTC, con perfil nuevo y sin preparar caché del motor: `passed`. Se abrió `win-unpacked` directamente en Windows, se recorrió la interfaz ES/EN y se completaron las tres descargas. FFprobe confirmó MP3 (7 766 828 bytes), AV1/AAC (22 967 690) y MP4 H.264/AAC (37 610 585). Los hashes de siete artefactos y tres descargas se conservaron; no quedaron procesos propios abiertos.

- Instalador de prueba SHA-256: `F4758D334AB17CEB0A7CC73D05E4CC03B13B897CC34225988BF06FEE0822562B`.
- `app.asar` SHA-256: `09218ACF267B8E9319B946E534206F985E8E0EC4578BF113A9D23BB70DCD3C6B`.
- Evidencia local: `electron/test-artifacts/packaged-smoke-20261009-180028-061/`, con `evidence.json`, `source-commit.txt`, `ui-result.json` y capturas. Son archivos de ejecución excluidos de Git; este informe no presume su disponibilidad en otro equipo.

El instalador se construyó e identificó, pero no se instaló. Authenticode es `NotSigned`, `installer_lifecycle_verified: false` y `public_release_ready: false`. Este smoke no acredita instalación/desinstalación sin runtimes externos ni la matriz manual completa. Las actualizaciones posteriores de este informe son documentales y no cambian el commit atribuido al paquete.

La ejecución nativa significa instalar y abrir Dr. Download directamente en Windows, con Electron, backend PyInstaller y runtimes incluidos. No significa una reescritura WinUI/C++. Una VM o un equipo físico Windows limpio sirven para comprobar independencia del entorno de desarrollo; la VM nunca es requisito del usuario. El ciclo del instalador y la firma siguen pendientes de su propia evidencia.
