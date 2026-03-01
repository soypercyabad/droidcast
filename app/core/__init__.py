"""
app.core — Lógica de negocio (ADB, scrcpy).
"""

from app.core.adb import run_adb, validate_ip, validate_port, get_adb_path
from app.core.scrcpy import (
    run_scrcpy,
    download_and_extract,
    close_processes,
    get_scrcpy_path,
)

__all__ = [
    "run_adb", "validate_ip", "validate_port", "get_adb_path",
    "run_scrcpy", "download_and_extract", "close_processes",
    "get_scrcpy_path",
]

