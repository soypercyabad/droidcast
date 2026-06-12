# ══════════════════════════════════════════════════════════════════════════════
# app/config.py — Configuración JSON persistente
# ══════════════════════════════════════════════════════════════════════════════

import json
import os
import sys
import logging

logger = logging.getLogger(__name__)

# ── Directorio base (compatible con PyInstaller) ─────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    ASSETS_DIR = sys._MEIPASS  # Recursos empaquetados por PyInstaller
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR = BASE_DIR

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def load():
    """Carga (root_path, ip, port, phone_frame) desde config.json."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return (
                data.get("root_path", ""), 
                data.get("ip", ""), 
                data.get("port", ""),
                data.get("phone_frame", True)
            )
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error al cargar configuración: {e}")
    return "", "", "", True


def save(root_path, ip, port="", phone_frame=True):
    """Guarda la configuración en config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "root_path": root_path, 
                "ip": ip, 
                "port": port,
                "phone_frame": phone_frame
            }, f, indent=2)
    except IOError as e:
        logger.error(f"Error al guardar configuración: {e}")


def _migrate_pickle():
    """Migra config.pkl antiguo a config.json (una sola vez)."""
    old_pkl = os.path.join(BASE_DIR, "config.pkl")
    if os.path.exists(old_pkl) and not os.path.exists(CONFIG_FILE):
        try:
            import pickle
            with open(old_pkl, "rb") as f:
                old = pickle.load(f)
            save(old.get("root_path", ""), old.get("ip", ""), old.get("port", ""))
            os.remove(old_pkl)
        except Exception:
            pass


# Ejecutar migración al importar
_migrate_pickle()
