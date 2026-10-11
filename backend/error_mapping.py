"""Safe, structured errors exposed by the local API and desktop UI."""


# yt-dlp signatures for "could not read the browser's cookie store". These mean
# cookies are unavailable (usually the browser is open and locking its DB), not
# that the content itself failed — so callers can retry without cookies.
_SESSION_MARKERS = ("dpapi", "decrypt")
_LOCK_MARKERS = ("cookie database", "permission denied", "permissionerror")


def is_browser_cookie_error(message: str) -> bool:
    """True when the failure is only about reading browser cookies."""
    text = (message or "").lower()
    return any(marker in text for marker in _SESSION_MARKERS + _LOCK_MARKERS)


def classify_error(message: str, cookie_source: str = "none") -> dict[str, str]:
    text = (message or "").lower()
    browser = "Edge" if cookie_source == "edge" else "Firefox"
    if "browser consent required" in text:
        return {
            "code": "browser_consent_required",
            "message": "El acceso a la sesión del navegador no está autorizado.",
            "recovery": "Autoriza el navegador seleccionado en Ajustes o continúa sin cookies para contenido público.",
        }
    if "sign in to confirm your age" in text:
        recovery = (
            "En Ajustes, selecciona Edge o Firefox como fuente de cookies. "
            "Inicia sesión en YouTube con una cuenta que pueda ver el vídeo y vuelve a analizar el enlace."
            if cookie_source == "none" else
            f"Abre el vídeo en {browser} con una cuenta con la edad verificada; "
            f"después cierra {browser} y vuelve a analizar el enlace."
        )
        return {
            "code": "age_restricted",
            "message": "YouTube exige iniciar sesión para verificar la edad y acceder a este vídeo.",
            "recovery": recovery,
        }
    if any(marker in text for marker in _SESSION_MARKERS):
        return {
            "code": "session_required",
            "message": "No se pudo leer la sesión protegida del navegador.",
            "recovery": f"Vuelve a iniciar sesión en {browser}, ciérralo completamente y reintenta.",
        }
    if any(marker in text for marker in _LOCK_MARKERS):
        return {
            "code": "browser_locked",
            "message": "El navegador mantiene bloqueada su sesión.",
            "recovery": f"Cierra todas las ventanas y procesos en segundo plano de {browser} y reintenta.",
        }
    if "no space" in text or "disk full" in text:
        return {
            "code": "disk_full",
            "message": "No hay espacio suficiente para completar la descarga.",
            "recovery": "Libera espacio o elige otra carpeta de destino.",
        }
    if "ffmpeg is unavailable" in text:
        return {
            "code": "ffmpeg_missing",
            "message": "Falta FFmpeg: sin él el vídeo se descargaría sin audio.",
            "recovery": "Coloca ffmpeg.exe y ffprobe.exe en electron/resources/ffmpeg o reinstala la aplicación.",
        }
    if "format is not available" in text or "requested format" in text:
        return {
            "code": "format_unavailable",
            "message": "El formato seleccionado ya no está disponible.",
            "recovery": "Analiza nuevamente el enlace y elige otro formato.",
        }
    if any(value in text for value in ("network", "timeout", "timed out", "connection")):
        return {
            "code": "network_error",
            "message": "La conexión se interrumpió durante la operación.",
            "recovery": "Comprueba la conexión y vuelve a intentarlo.",
        }
    return {
        "code": "engine_error",
        "message": "El motor no pudo completar la operación.",
        "recovery": "Actualiza el motor y vuelve a intentarlo.",
    }
