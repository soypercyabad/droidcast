"""
app.core — Lógica de negocio (ADB, scrcpy, dispositivo, capturas, APKs).
"""

from app.core.adb import run_adb, validate_ip, validate_port, get_adb_path
from app.core.scrcpy import (
    run_scrcpy,
    download_and_extract,
    close_processes,
    get_scrcpy_path,
)
from app.core.device import (
    check_connection,
    get_device_info,
    get_manufacturer,
    needs_security_debug_warning,
    connect,
    disconnect,
)
from app.core.screenshot import capture_raw, capture_to_file, capture_to_clipboard
from app.core.apk_manager import (
    install,
    RESULT_SUCCESS,
    RESULT_USER_RESTRICTED,
    RESULT_INSUFFICIENT_STORAGE,
    RESULT_TIMEOUT,
    RESULT_ERROR,
)

__all__ = [
    # adb
    "run_adb", "validate_ip", "validate_port", "get_adb_path",
    # scrcpy
    "run_scrcpy", "download_and_extract", "close_processes", "get_scrcpy_path",
    # device
    "check_connection", "get_device_info", "get_manufacturer",
    "needs_security_debug_warning", "connect", "disconnect",
    # screenshot
    "capture_raw", "capture_to_file", "capture_to_clipboard",
    # apk_manager
    "install", "RESULT_SUCCESS", "RESULT_USER_RESTRICTED",
    "RESULT_INSUFFICIENT_STORAGE", "RESULT_TIMEOUT", "RESULT_ERROR",
]

