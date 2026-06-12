# ══════════════════════════════════════════════════════════════════════════════
# app/core/apk_manager.py — Instalación y gestión de APKs vía ADB
# ══════════════════════════════════════════════════════════════════════════════

import logging

from app.core.adb import run_adb

logger = logging.getLogger(__name__)


# ── Códigos de resultado ──────────────────────────────────────────────────────

RESULT_SUCCESS             = "success"
RESULT_USER_RESTRICTED     = "user_restricted"
RESULT_INSUFFICIENT_STORAGE = "insufficient_storage"
RESULT_TIMEOUT             = "timeout"
RESULT_ERROR               = "error"


# ── Instalación ───────────────────────────────────────────────────────────────

def install(apk_path: str) -> tuple[str, str]:
    """
    Instala un APK en el dispositivo conectado.

    Args:
        apk_path: ruta local al archivo .apk

    Retorna:
        (result_code, raw_output)
        result_code: una de las constantes RESULT_* de este módulo
    """
    try:
        stdout, stderr, _ = run_adb(["install", "-r", apk_path])
        output = f"{stdout}\n{stderr}"

        if "Success" in stdout:
            logger.info(f"APK instalado correctamente: {apk_path}")
            return RESULT_SUCCESS, output

        if "INSTALL_FAILED_USER_RESTRICTED" in output:
            logger.warning("Instalación bloqueada por restricción de usuario")
            return RESULT_USER_RESTRICTED, output

        if "INSTALL_FAILED_INSUFFICIENT_STORAGE" in output:
            logger.warning("Sin espacio suficiente en el dispositivo")
            return RESULT_INSUFFICIENT_STORAGE, output

        if "Tiempo de espera agotado" in output:
            logger.warning("Tiempo de espera agotado durante la instalación")
            return RESULT_TIMEOUT, output

        logger.error(f"Error desconocido al instalar: {output.strip()}")
        return RESULT_ERROR, output.strip()

    except Exception as e:
        logger.error(f"Excepción al instalar APK '{apk_path}': {e}")
        return RESULT_ERROR, str(e)
