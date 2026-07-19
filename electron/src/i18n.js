export const messages = {
  es: {
    new: "Nueva descarga", queue: "Cola", history: "Historial", settings: "Ajustes",
    about: "Acerca de", url: "Enlace del video", inspect: "Analizar enlace", inspecting: "Analizando…",
    pasteHint: "Pega un enlace compatible para preparar la descarga.", format: "Formato y calidad",
    folder: "Carpeta de destino", choose: "Elegir carpeta", add: "Agregar a la cola",
    queued: "En cola", downloading: "Descargando", postprocessing: "Procesando",
    completed: "Completada", failed: "Fallida", cancelled: "Cancelada", cancel: "Cancelar",
    retry: "Reintentar", openFile: "Abrir archivo", openFolder: "Abrir carpeta", remove: "Eliminar",
    emptyQueue: "No hay descargas activas.", emptyHistory: "Tu historial aparecerá aquí.",
    language: "Idioma", browser: "Sesión del navegador", notifications: "Notificaciones al finalizar",
    save: "Guardar cambios", consentTitle: "Uso privado de tu sesión",
    consentBody: "Dr. Download puede leer temporalmente la sesión del navegador que elijas. No copia ni almacena cookies.",
    consent: "Autorizar uso", legal: "Descarga únicamente contenido que tengas autorización para guardar.",
    ready: "Señal preparada", duration: "Duración", author: "Autor", version: "Versión",
    aboutCopy: "Herramienta local para preparar y descargar contenido multimedia con control y privacidad.",
    errorTitle: "No se pudo completar la operación", unknownError: "Comprueba el enlace, la conexión y la sesión del navegador.",
    speed: "Velocidad", eta: "Restante", size: "Transferido", folderReady: "Carpeta lista",
    folderInvalid: "La carpeta no está disponible. Elige otra o usa Descargas.", useDownloads: "Usar carpeta Descargas",
    exportDiagnostics: "Exportar diagnóstico"
  },
  en: {
    new: "New download", queue: "Queue", history: "History", settings: "Settings",
    about: "About", url: "Video link", inspect: "Inspect link", inspecting: "Inspecting…",
    pasteHint: "Paste a supported link to prepare the download.", format: "Format and quality",
    folder: "Destination folder", choose: "Choose folder", add: "Add to queue",
    queued: "Queued", downloading: "Downloading", postprocessing: "Processing",
    completed: "Completed", failed: "Failed", cancelled: "Cancelled", cancel: "Cancel",
    retry: "Retry", openFile: "Open file", openFolder: "Open folder", remove: "Remove",
    emptyQueue: "There are no active downloads.", emptyHistory: "Your history will appear here.",
    language: "Language", browser: "Browser session", notifications: "Completion notifications",
    save: "Save changes", consentTitle: "Private session access",
    consentBody: "Dr. Download can temporarily read the browser session you choose. Cookies are never copied or stored.",
    consent: "Allow access", legal: "Only download content you are authorized to save.",
    ready: "Signal ready", duration: "Duration", author: "Author", version: "Version",
    aboutCopy: "A local tool for preparing and downloading media with control and privacy.",
    errorTitle: "The operation could not be completed", unknownError: "Check the link, connection and browser session.",
    speed: "Speed", eta: "Remaining", size: "Transferred", folderReady: "Folder ready",
    folderInvalid: "This folder is unavailable. Choose another or use Downloads.", useDownloads: "Use Downloads folder",
    exportDiagnostics: "Export diagnostics"
  }
};

export function translator(language) {
  const selected = messages[language] || messages.es;
  return (key) => selected[key] || key;
}
