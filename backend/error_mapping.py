"""Safe, structured errors exposed by the local API and desktop UI."""


def classify_error(message: str, cookie_source: str = "none") -> dict[str, str]:
    text = (message or "").lower()
    browser = "Edge" if cookie_source == "edge" else "Firefox"
    if "dpapi" in text or "decrypt" in text:
        return {
            "code": "session_required",
            "message": "No se pudo leer la sesión protegida del navegador.",
            "recovery": f"Vuelve a iniciar sesión en {browser}, ciérralo completamente y reintenta.",
        }
    if "cookie database" in text or "permission denied" in text or "permissionerror" in text:
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
