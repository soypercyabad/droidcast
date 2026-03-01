# ══════════════════════════════════════════════════════════════════════════════
# app/core/scrcpy.py — Descarga, versión y ejecución de scrcpy
# ══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import subprocess
import threading
import logging
import urllib.request
import zipfile
import winreg

import requests

from app.config import BASE_DIR, load, save
from app.theme import Theme

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/Genymobile/scrcpy/releases/latest"
_scrcpy_info = {"url": None, "version": None, "resolved": False}

# Variable global para el proceso activo
scrcpy_process = None


# ── Resolución de versiones ──────────────────────────────────────────────────

def obtener_url_ultima_version():
    """Consulta GitHub API para obtener la URL de la última versión de scrcpy."""
    try:
        response = requests.get(GITHUB_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        version = data["tag_name"]
        for asset in data["assets"]:
            if "win64" in asset["name"]:
                return asset["browser_download_url"], version
        return None, None
    except requests.RequestException as e:
        logger.error(f"Error al obtener versión: {e}")
        return None, None


def _resolve_scrcpy_info():
    if _scrcpy_info["resolved"]:
        return _scrcpy_info["url"] is not None
    url, version = obtener_url_ultima_version()
    _scrcpy_info.update({"url": url, "version": version, "resolved": True})
    return version is not None


def _find_existing_scrcpy():
    try:
        for item in os.listdir(BASE_DIR):
            path = os.path.join(BASE_DIR, item)
            if os.path.isdir(path) and item.startswith("scrcpy"):
                exe = os.path.join(path, "scrcpy.exe")
                if os.path.exists(exe):
                    return exe
    except OSError:
        pass
    return None


def get_local_version():
    """Obtiene la versión local de scrcpy desde el nombre de la carpeta."""
    try:
        for item in os.listdir(BASE_DIR):
            path = os.path.join(BASE_DIR, item)
            if os.path.isdir(path) and item.startswith("scrcpy-"):
                exe = os.path.join(path, "scrcpy.exe")
                if os.path.exists(exe):
                    return item.replace("scrcpy-", ""), path
    except OSError:
        pass
    return None, None


def _remove_old_folders(keep_version):
    """Elimina carpetas scrcpy-* anteriores, excepto la versión indicada."""
    import time as _time
    keep_folder = f"scrcpy-{keep_version}"
    try:
        for item in os.listdir(BASE_DIR):
            path = os.path.join(BASE_DIR, item)
            if (os.path.isdir(path) and item.startswith("scrcpy-")
                    and item != keep_folder and not item.endswith(".zip")):
                for attempt in range(3):
                    try:
                        shutil.rmtree(path)
                        logger.info(f"Versión anterior eliminada: {item}")
                        break
                    except PermissionError:
                        logger.warning(f"Intento {attempt+1}/3 - Archivos bloqueados en {item}")
                        _time.sleep(2)
                    except Exception as e:
                        logger.error(f"Error al eliminar {item}: {e}")
                        break
    except OSError:
        pass


def get_scrcpy_path():
    """Retorna la ruta al ejecutable scrcpy.exe."""
    if _scrcpy_info["version"]:
        p = os.path.join(BASE_DIR, f"scrcpy-{_scrcpy_info['version']}", "scrcpy.exe")
        if os.path.exists(p):
            return p
    return _find_existing_scrcpy()


def add_to_user_path(new_path):
    """Agrega una ruta al PATH del usuario en el registro de Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                current = winreg.QueryValueEx(key, "Path")[0]
            except FileNotFoundError:
                current = ""
            if new_path not in current:
                updated = f"{current};{new_path}" if current else new_path
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, updated)
    except Exception as e:
        logger.error(f"Error al agregar al PATH: {e}")


# ── Descarga ─────────────────────────────────────────────────────────────────

def download_and_extract(root):
    """Descarga y extrae scrcpy desde GitHub."""
    from app.ui.dialogs import ProgressOverlay, ResultDialog
    overlay = ProgressOverlay(root, "Descargando scrcpy...")

    def _download():
        try:
            overlay.update_status("Obteniendo información de versión...")
            if not _resolve_scrcpy_info() or not _scrcpy_info["url"]:
                raise Exception("No se pudo obtener la URL. Verifique su conexión a internet.")
            version = _scrcpy_info["version"]
            zip_path = os.path.join(BASE_DIR, f"scrcpy-{version}.zip")
            folder_path = os.path.join(BASE_DIR, f"scrcpy-{version}")

            overlay.update_status(f"Descargando scrcpy {version}...")

            def _reporthook(block_num, block_size, total_size):
                if total_size > 0:
                    downloaded = block_num * block_size
                    pct = min(downloaded / total_size, 1.0)
                    overlay.update_progress(pct * 0.7)
                    mb_down = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    overlay.update_status(
                        f"Descargando scrcpy {version}... {mb_down:.1f}/{mb_total:.1f} MB")

            urllib.request.urlretrieve(_scrcpy_info["url"], zip_path, _reporthook)

            overlay.update_status("Extrayendo archivos...")
            overlay.update_progress(0.75)
            os.makedirs(folder_path, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(folder_path)
            os.remove(zip_path)

            overlay.update_status("Organizando archivos...")
            overlay.update_progress(0.9)
            folders = [f for f in os.listdir(folder_path)
                       if os.path.isdir(os.path.join(folder_path, f))]
            if folders:
                nested = os.path.join(folder_path, folders[0])
                for item in os.listdir(nested):
                    dst = os.path.join(folder_path, item)
                    if not os.path.exists(dst):
                        shutil.move(os.path.join(nested, item), folder_path)
                try:
                    os.rmdir(nested)
                except OSError:
                    pass

            overlay.update_status("Configurando PATH...")
            overlay.update_progress(0.88)
            add_to_user_path(folder_path)

            overlay.update_status("Deteniendo procesos...")
            overlay.update_progress(0.92)
            for proc_name in ["adb.exe", "scrcpy.exe"]:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", proc_name],
                        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                except Exception:
                    pass
            import time; time.sleep(2)

            overlay.update_status("Eliminando versión anterior...")
            overlay.update_progress(0.96)
            _remove_old_folders(version)

            overlay.update_status("Reiniciando servidor ADB...")
            overlay.update_progress(0.98)
            new_adb = os.path.join(folder_path, "adb.exe")
            if os.path.exists(new_adb):
                try:
                    subprocess.run(
                        [new_adb, "start-server"],
                        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    _, saved_ip, saved_port = load()
                    if saved_ip:
                        port = saved_port or "5555"
                        subprocess.run(
                            [new_adb, "connect", f"{saved_ip}:{port}"],
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                except Exception:
                    pass

            overlay.update_progress(1.0)
            overlay.update_status("¡Completado!")
            import time; time.sleep(0.5)
            root.after(0, overlay.close)
            root.after(10, lambda: ResultDialog(root,
                "Descarga completada",
                f"scrcpy {version} descargado correctamente.\nAhora puede transmitir su dispositivo.",
                "success"))
        except Exception as e:
            root.after(0, overlay.close)
            root.after(10, lambda: ResultDialog(root,
                "Error de descarga",
                "No se pudo descargar scrcpy.",
                "error", str(e)))
            return False
        return True

    threading.Thread(target=_download, daemon=True).start()
    return True


# ── Ejecución ────────────────────────────────────────────────────────────────

def run_scrcpy(root):
    """Ejecuta scrcpy. Validaciones en main thread, lanzamiento en background."""
    global scrcpy_process
    from app.ui.dialogs import ResultDialog, ConfirmDialog
    from app.core.adb import run_adb

    path = get_scrcpy_path()
    if not path:
        ResultDialog(root, "Plugin no encontrado",
            "scrcpy no está instalado.\nSe descargará automáticamente.",
            "info", wait=True)
        download_and_extract(root)
        return

    # Verificar dispositivo conectado (rápido, main thread OK)
    try:
        stdout, _, _ = run_adb(["devices"])
        lines = stdout.splitlines()
        has_device = any("device" in l and "offline" not in l for l in lines[1:])
        if not has_device:
            ResultDialog(root, "Sin dispositivo",
                "No hay ningún dispositivo conectado.\n"
                "Conecte un dispositivo por USB o Wi-Fi\nantes de transmitir.",
                "warning")
            return
    except Exception:
        pass

    # Si ya hay scrcpy corriendo, preguntar
    if scrcpy_process and scrcpy_process.poll() is None:
        confirm = ConfirmDialog(root, "Scrcpy en ejecución",
                                "Ya hay una transmisión activa.\n¿Desea reiniciarla?")
        if not confirm.result:
            return
        try:
            scrcpy_process.terminate()
            scrcpy_process.wait(timeout=2)
        except Exception:
            pass

    # Todo lo demás (version check + xiaomi check + launch) en background
    def _background():
        global scrcpy_process
        nonlocal path

        # 1) Version check (red) — si hay update, preguntar en main thread
        try:
            local_ver, _ = get_local_version()
            if local_ver and _resolve_scrcpy_info() and _scrcpy_info["version"]:
                remote_ver = _scrcpy_info["version"]
                if local_ver != remote_ver:
                    import threading as _th
                    result = {"update": False, "done": _th.Event()}

                    def _ask_update():
                        c = ConfirmDialog(root, "Actualización disponible",
                            f"Versión instalada: {local_ver}\n"
                            f"Versión disponible: {remote_ver}\n\n"
                            "¿Desea actualizar antes de transmitir?")
                        result["update"] = c.result
                        result["done"].set()

                    root.after(0, _ask_update)
                    result["done"].wait(timeout=30)

                    if result["update"]:
                        root.after(0, lambda: download_and_extract(root))
                        return
        except Exception:
            pass

        # 2) Xiaomi/POCO check — avisar en main thread, esperar aceptación
        try:
            stdout, _, _ = run_adb(["shell", "getprop", "ro.product.manufacturer"])
            mfg = stdout.strip().lower()
            if any(x in mfg for x in ["xiaomi", "redmi", "poco", "realme", "oppo", "vivo"]):
                import threading as _th
                done_event = _th.Event()

                def _show_warning():
                    ResultDialog(root,
                        "Nota para tu dispositivo",
                        "En dispositivos Xiaomi/Redmi/POCO, debes activar:\n"
                        "'Depuración USB (Ajustes de seguridad)'\nen Opciones de desarrollador.",
                        "info",
                        "Si no funciona el control táctil,\nreinicia el dispositivo.",
                        wait=True)
                    done_event.set()

                root.after(0, _show_warning)
                done_event.wait(timeout=60)
        except Exception:
            pass

        # 3) Lanzar scrcpy
        try:
            scrcpy_process = subprocess.Popen(
                [path], creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as e:
            root.after(0, lambda: ResultDialog(root,
                "Error", "No se pudo iniciar scrcpy.",
                "error", str(e)))

    threading.Thread(target=_background, daemon=True).start()


def close_processes():
    """Termina el proceso scrcpy si está activo. Se registra con atexit."""
    global scrcpy_process
    if scrcpy_process:
        try:
            scrcpy_process.terminate()
        except Exception:
            pass
        scrcpy_process = None
