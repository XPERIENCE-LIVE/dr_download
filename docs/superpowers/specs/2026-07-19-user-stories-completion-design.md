# Diseño de completitud de historias US-010–US-053

## Objetivo

Convertir las 21 historias resumidas en contratos SDD verificables y honestos, sin confundir una prueba planificada con evidencia ya ejecutada.

## Diseño aprobado

Cada ficha contiene ID, épica, persona, problema, precondiciones, flujo principal, flujos alternativos, Given/When/Then, prueba unitaria, integración, E2E, evidencia y riesgos. Las pruebas existentes se nombran exactamente; las ausentes usan un ID estable `GAP-US-###-*`. Las matrices contienen una fila por historia y nunca agregan varias historias bajo un estado ambiguo.

## Reglas de estado

- `covered`: existe prueba automatizada y evidencia fresca.
- `partial`: existe parte de la pirámide, pero falta integración, E2E o aceptación manual.
- `blocked`: depende de una condición externa explícita.
- `planned`: no existe aún prueba ejecutable.

## Autorrevisión

No se permiten `TBD`, historias agrupadas, evidencia inventada ni estado `accepted` sin trazabilidad completa.
