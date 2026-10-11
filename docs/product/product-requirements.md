# Requisitos de producto

## Propósito

Dr. Download permite preparar y descargar contenido autorizado desde una aplicación Windows local, clara y recuperable. No incluye cuentas, pagos, nube, telemetría ni biblioteca multimedia avanzada.

## Flujos

1. El usuario pega un enlace y selecciona si permite leer una sesión de Edge/Firefox.
2. La aplicación inspecciona el recurso sin descargarlo y muestra sus metadatos.
3. El usuario elige formato, calidad y carpeta; la tarea entra en una cola de ejecución individual.
4. La cola muestra estado y métricas disponibles sin acciones manuales; inspección y magnitudes desconocidas no reciben valores inventados.
5. Una tarea puede cancelarse, reintentarse, abrirse o eliminarse del historial.

## Criterios de aceptación

- Una instalación limpia funciona sin Node.js ni Python instalados.
- Ninguna cookie se copia a la base de datos, configuración o registros.
- El cierre de la ventana detiene el backend local.
- Los fallos muestran causa y recuperación; una actualización fallida no bloquea la versión instalada.
- Interfaz completa mediante teclado, foco visible, contraste AA y movimiento reducido.
- Español predeterminado e inglés seleccionable sin reiniciar.

## Experiencia confiable aprobada

US-062–US-066 exigen disponibilidad confirmada por lecturas, inspección indeterminada, encolado diferenciado, borrador de sesión, presets comprensibles, espacio estimado validado, recuperación ES/EN, guardado confirmado y consentimiento revocable. El Historial incorpora búsqueda local por título/URL/archivo y estado; un enlace repetido se advierte y puede repetirse intencionalmente sin debilitar la protección de archivos. El [contrato de experiencia](experience-reliability.md) define límites y escenarios; [ADR-003](../architecture/adr/ADR-003-experience-and-history.md) aprueba la ampliación. No implica aceptación ni publicación.

## Reproducción y listas aprobadas

US-067–US-072 añaden reproducción en streaming de enlaces individuales de YouTube y Vimeo sin el reproductor oficial ni sus anuncios, búsqueda con posición absoluta, salto opcional de patrocinios con consentimiento propio, listas locales, importación de listas por enlace con límite de 500 entradas y reproducción ordenada con aviso visible de ítems no disponibles. DRM y emisiones en directo se rechazan con causa y recuperación. El [contrato de reproducción](playback-and-playlists.md) define límites y umbrales; [ADR-004](../architecture/adr/ADR-004-streaming-playback-and-playlists.md) aprueba la ampliación y registra el riesgo de Términos de Servicio aceptado por producto. No implica aceptación ni publicación firmada.

