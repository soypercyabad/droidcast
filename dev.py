"""
Hot-Reload para Android Developer Tools
────────────────────────────────────────
Ejecutar: python dev.py

Vigila cambios en main.py y en toda la carpeta app/ y
reinicia la aplicación automáticamente al detectar modificaciones.

Requiere: pip install watchdog
"""
import subprocess
import sys
import time
import os

TARGET_FILE = "main.py"
WATCH_DIR = os.path.dirname(os.path.abspath(__file__))
WATCH_EXTENSIONS = {".py"}


def run_app():
    """Inicia la aplicación como subproceso."""
    return subprocess.Popen(
        [sys.executable, TARGET_FILE],
        cwd=WATCH_DIR,
    )


def _is_watchable(path):
    """Retorna True si el archivo debe disparar un reload."""
    _, ext = os.path.splitext(path)
    if ext not in WATCH_EXTENSIONS:
        return False
    # Ignorar __pycache__, .git, etc.
    parts = path.replace("\\", "/").split("/")
    return not any(p.startswith("__") or p.startswith(".") for p in parts)


def main():
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class ReloadHandler(FileSystemEventHandler):
            def __init__(self):
                self.process = None
                self.last_reload = 0

            def start_app(self):
                if self.process:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                print(f"\n{'='*50}")
                print(f"  🔄 Reiniciando aplicación...")
                print(f"{'='*50}\n")
                self.process = run_app()

            def on_modified(self, event):
                if event.is_directory:
                    return
                if not _is_watchable(event.src_path):
                    return
                now = time.time()
                if now - self.last_reload < 2:
                    return
                self.last_reload = now
                rel = os.path.relpath(event.src_path, WATCH_DIR)
                print(f"\n  📝 Cambio detectado: {rel}")
                self.start_app()

        handler = ReloadHandler()
        handler.start_app()

        observer = Observer()
        observer.schedule(handler, WATCH_DIR, recursive=True)
        observer.start()

        print("  👁️  Vigilando cambios... (Ctrl+C para salir)")
        print(f"  📁 Directorio: {WATCH_DIR}")
        print(f"  📄 Vigila: main.py + app/**/*.py\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            if handler.process:
                handler.process.terminate()
        observer.join()

    except ImportError:
        # Fallback: polling que revisa todos los .py recursivamente
        print("  ⚠️  watchdog no instalado. Usando polling básico.")
        print("  💡 Para mejor rendimiento: pip install watchdog\n")

        def _get_all_mtimes():
            mtimes = {}
            for root_dir, dirs, files in os.walk(WATCH_DIR):
                # Ignorar carpetas ocultas y __pycache__
                dirs[:] = [d for d in dirs if not d.startswith("__") and not d.startswith(".")]
                for f in files:
                    if f.endswith(".py"):
                        fp = os.path.join(root_dir, f)
                        try:
                            mtimes[fp] = os.path.getmtime(fp)
                        except OSError:
                            pass
            return mtimes

        process = run_app()
        last_mtimes = _get_all_mtimes()

        print("  👁️  Vigilando cambios... (Ctrl+C para salir)\n")

        try:
            while True:
                time.sleep(2)
                current_mtimes = _get_all_mtimes()
                changed = False
                for fp, mtime in current_mtimes.items():
                    if fp not in last_mtimes or last_mtimes[fp] != mtime:
                        rel = os.path.relpath(fp, WATCH_DIR)
                        print(f"\n  📝 Cambio detectado: {rel}")
                        changed = True
                        break
                if changed:
                    last_mtimes = current_mtimes
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    process = run_app()
        except KeyboardInterrupt:
            process.terminate()

    print("\n  ✅ Dev server detenido.")


if __name__ == "__main__":
    main()
