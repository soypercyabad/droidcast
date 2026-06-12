# ══════════════════════════════════════════════════════════════════════════════
# app/core/device.py — Gestión de la conexión y estado del dispositivo ADB
# ══════════════════════════════════════════════════════════════════════════════

import logging

from app.core.adb import run_adb

logger = logging.getLogger(__name__)

# Fabricantes que requieren aviso especial de depuración
_SPECIAL_MANUFACTURERS = ("xiaomi", "redmi", "poco", "realme", "oppo", "vivo")


# ── Estado de conexión ────────────────────────────────────────────────────────

def check_connection() -> bool:
    """Verifica si hay al menos un dispositivo ADB conectado y no offline."""
    try:
        stdout, _, _ = run_adb(["devices"], timeout=10)
        lines = stdout.splitlines()
        return any("device" in line and "offline" not in line for line in lines[1:])
    except Exception as e:
        logger.error(f"Error al verificar conexión: {e}")
        return False


def get_device_info() -> dict:
    """
    Obtiene información del dispositivo conectado via getprop.
    Retorna dict con claves: model, version, sdk, manufacturer.
    Retorna dict vacío si no hay dispositivo.
    """
    try:
        model, _, _     = run_adb(["shell", "getprop", "ro.product.model"],       timeout=8)
        version, _, _   = run_adb(["shell", "getprop", "ro.build.version.release"], timeout=8)
        sdk, _, _       = run_adb(["shell", "getprop", "ro.build.version.sdk"],    timeout=8)
        mfg, _, _       = run_adb(["shell", "getprop", "ro.product.manufacturer"], timeout=8)
        return {
            "model":        model.strip()   or "Desconocido",
            "version":      version.strip() or "?",
            "sdk":          sdk.strip()     or "",
            "manufacturer": mfg.strip().lower(),
        }
    except Exception as e:
        logger.error(f"Error al obtener info del dispositivo: {e}")
        return {}


def get_manufacturer() -> str:
    """
    Retorna el fabricante del dispositivo en minúsculas.
    Útil para detectar Xiaomi/POCO/etc.
    """
    try:
        stdout, _, _ = run_adb(["shell", "getprop", "ro.product.manufacturer"], timeout=8)
        return stdout.strip().lower()
    except Exception:
        return ""


def needs_security_debug_warning(manufacturer: str) -> bool:
    """True si el fabricante requiere aviso sobre 'Depuración USB (Ajustes de seguridad)'."""
    return any(x in manufacturer for x in _SPECIAL_MANUFACTURERS)


# ── Conexión / Desconexión ────────────────────────────────────────────────────

def connect(ip: str, port: str) -> tuple[bool, str, str]:
    """
    Conecta al dispositivo por ADB Wi-Fi.
    Reinicia el servidor ADB antes de conectar.

    Retorna:
        (success, status_key, message)
        status_key: 'connected' | 'already_connected' | 'error'
    """
    try:
        run_adb(["kill-server"],  timeout=15)
        run_adb(["start-server"], timeout=15)
        stdout, stderr, _ = run_adb(["connect", f"{ip}:{port}"], timeout=20)

        if "connected to" in stdout:
            return True, "connected", f"Conectado por Wi-Fi en {ip}:{port}"
        elif "already connected" in stdout:
            return True, "already_connected", f"El dispositivo ya está conectado a {ip}:{port}"
        else:
            return False, "error", f"{stdout}\n{stderr}".strip()
    except Exception as e:
        logger.error(f"Error al conectar a {ip}:{port} — {e}")
        return False, "error", str(e)


def disconnect() -> bool:
    """
    Desconecta todos los dispositivos ADB.
    Retorna True si el comando se ejecutó sin excepción.
    """
    try:
        run_adb(["disconnect"], timeout=10)
        return True
    except Exception as e:
        logger.error(f"Error al desconectar: {e}")
        return False
