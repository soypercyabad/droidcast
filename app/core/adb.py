# ══════════════════════════════════════════════════════════════════════════════
# app/core/adb.py — Comandos ADB y validación de entrada
# ══════════════════════════════════════════════════════════════════════════════

import re
import subprocess
import logging

logger = logging.getLogger(__name__)


def get_adb_path():
    """Obtiene la ruta al ejecutable adb (bundled con scrcpy)."""
    from app.core.scrcpy import get_scrcpy_path
    import os
    sp = get_scrcpy_path()
    if sp:
        adb = os.path.join(os.path.dirname(sp), "adb.exe")
        if os.path.exists(adb):
            return adb
    return "adb"


def run_adb(args, timeout: int = 120):
    """
    Ejecuta un comando ADB. Retorna (stdout, stderr, returncode).

    Args:
        args:    lista de argumentos ADB (sin el ejecutable).
        timeout: segundos máximos de espera. Usar valores pequeños (8-15)
                 para comandos rápidos como getprop o devices.
    """
    try:
        result = subprocess.run(
            [get_adb_path()] + args,
            capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", "adb no encontrado. Instale scrcpy primero.", 1
    except subprocess.TimeoutExpired:
        return "", "Tiempo de espera agotado.", 1


def validate_ip(ip):
    """Valida una dirección IPv4."""
    if not ip:
        return False
    if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", ip):
        return False
    return all(0 <= int(p) <= 255 for p in ip.split("."))


def validate_port(port):
    """Valida un número de puerto (1-65535)."""
    try:
        return 1 <= int(port) <= 65535 if port else False
    except ValueError:
        return False
