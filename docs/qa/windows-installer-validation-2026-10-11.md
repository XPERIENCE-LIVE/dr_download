# Validación Windows sin VM local — 2026-10-11

Esta evidencia corresponde a los candidatos identificados abajo. No acredita candidatos posteriores ni habilita publicación. La aplicación se ejecuta directamente en Windows; no se necesita virtualización para usarla.

## Instalación y desinstalación reales en GitHub

[Run 38117705361](https://github.com/XPERIENCE-LIVE/dr_download/actions/runs/38117705361), head `05fbd130a807da3a2967b507c70461c2a3bbf304`, checkout `dc3ad5e2f0f1ab41143b3818f9298d76fb15690b`, artifact-id unsigned `11694237743`:

```text
NSIS SHA-256: 0A547AECECD5AABC7453B225131A3E83C3CC5D110BF9B9A9B06B2349A03ADC13
SO: Windows Server 2025 Datacenter 10.0.26100
Imagen GitHub: 20260925.250.1
Instalación: exit 0
Desinstalación: exit 0
uninstall_verified: true
user_data_preserved: true
status: failed
publishable: false
```

El NSIS se instaló en un runner nuevo con Python/Node/FFmpeg externos fuera de PATH. Se verificaron accesos y registro; la UI real inició, cambió ES/EN y guardó ajustes. La desinstalación eliminó el directorio instalado, accesos y registro, conservando los hashes de `config.json` y `downloads.db`.

El smoke completo falló al inspeccionar el enlace de YouTube. La captura mostró un error genérico del motor; no hay evidencia suficiente para atribuirlo al bloqueo de una IP de GitHub. La limpieza también encontró un proceso ya terminado. El fallo completo se mantiene registrado aunque la desinstalación haya pasado.

La corrección posterior tolera únicamente el caso de proceso ya terminado y conserva la comprobación final de procesos propios. PR comprueba instalación/arranque/ajustes/desinstalación con alcance explícito `startup`; nightly y release mantienen las tres descargas reales. El gate de firma rechaza evidencia startup. Consultar [el contrato vigente](../release/windows-release.md).

## Ejecución nativa en el Windows 10 del mantenedor

Paquete del [run 38116757542](https://github.com/XPERIENCE-LIVE/dr_download/actions/runs/38116757542), head `cc3c0803980a88301e2cb904b069ae65ee6b17f4`, checkout `75f92f0a30c0255cbed0ddd36c200e667270702c`, artifact-id `11693890897`. Scripts QA de `05fbd130a807da3a2967b507c70461c2a3bbf304`:

```text
NSIS SHA-256: CCC31327C963BA6FB5175A8FF0CAD542138F5BF38395AA6CD42F0F59AA86C866
SO: Windows 10 Home 10.0.19045 x64
Smoke UI completo: passed
MP3: 7 766 828 bytes; mp3
Máxima calidad: 22 967 690 bytes; av1/aac
Compatible: 37 610 585 bytes; h264/aac
```

El candidato de GitHub se extrajo sin ejecutar NSIS ni modificar la instalación habitual. Se usaron backend, Node y FFmpeg empaquetados, con PATH limitado a Windows/PowerShell. Pasaron UI ES/EN, IPC, ajustes, borrador, inspección, historial y tres descargas reales verificadas con FFprobe. Se comprobaron nuevamente los hashes de siete artefactos y tres archivos descargados; no quedaron procesos propios abiertos. Evidencia local: `artifacts/quality/native-win10-cc3/evidence.json` y `provenance.json`.

## Pendientes reales

Windows Server con herramientas fuera de PATH y Windows 10 de desarrollo no acreditan instalación en Windows 10/11 limpio. Esa matriz, actualización y roll-forward permanecen pendientes. El test local anterior tampoco acredita instalación NSIS.

No hay certificado local ni configuración aprobada de SignPath disponible. La integración está preparada, pero no se ha obtenido ni probado una firma real. [SignPath Foundation](https://signpath.org/) ofrece una vía gratuita para OSS sujeta a admisión; requiere actuación del titular y aprobación externa. No se usa firma autofirmada ni se ha publicado una release.
