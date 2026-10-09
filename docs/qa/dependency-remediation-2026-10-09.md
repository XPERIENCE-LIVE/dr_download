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

## Evidencia

La auditoría previa está conservada localmente en `artifacts/quality/npm-audit-moderate-before.json`. `npm ci` con npm 10.9.9 completó una instalación nueva con código 0. Las auditorías posteriores de todo el árbol y de producción registran cero vulnerabilidades en `artifacts/quality/npm-audit-moderate-after.json` y `npm-audit-production-after.json`. Las tres pruebas de compatibilidad pasan después de instalar; `npm ls` confirma YAML 4.3.2, global-agent 4.1.3 y ausencia de sprintf-js. No se actualizaron las otras versiones directas ni el runtime Electron.

El gate PR local del árbol de trabajo pasó: 217 pytest, 96 Jest, contratos, integridad Python, lint, build y audit moderado. La construcción Windows requiere evidencia propia del cambio. Los resultados del [paquete anterior](reliable-workflows-validation.md) permanecen atribuidos a su commit y no certifican este cambio. Cero avisos npm significa cero hallazgos conocidos por esa auditoría en ese momento, no una garantía de ausencia de defectos o una auditoría completa de los binarios incluidos.

La ejecución nativa significa instalar y abrir Dr. Download directamente en Windows, con Electron, backend PyInstaller y runtimes incluidos. No significa una reescritura WinUI/C++. Una VM o un equipo físico Windows limpio sirven para comprobar independencia del entorno de desarrollo; la VM nunca es requisito del usuario. El ciclo del instalador y la firma siguen pendientes de su propia evidencia.
