# ══════════════════════════════════════════════════════════════════════════════
# app/ui/scrcpy_overlay.py — Pill flotante sobre la ventana de scrcpy
# ══════════════════════════════════════════════════════════════════════════════

import ctypes
import os
import ctypes.wintypes
import threading
import logging
from app import config
from PIL import Image, ImageTk

import customtkinter as ctk

from app.theme import Theme

logger = logging.getLogger(__name__)

_PILL_W   = 150    # ancho estimado del pill para centrado
_KEY      = "#010101"  # color clave para transparencia de ventana (nunca usarlo en widgets)
_PILL_BG  = "#111827"  # fondo del pill
_BORDER   = "#374151"  # borde del pill
_BTN_BG   = "#1F2937"  # fondo del botón cámara


# ── Helpers Win32 ─────────────────────────────────────────────────────────────

def _load_local_image(filename, size=None):
    try:
        path = os.path.join(config.ASSETS_DIR, "assets", "icons", filename)
        if not os.path.exists(path):
            return None
        img = Image.open(path).convert("RGBA")
        if size:
            img = img.resize(size, Image.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size if size else img.size)
    except Exception as e:
        logger.warning(f"Error loading local image {filename}: {e}")
        return None

def _find_window_by_pid(pid: int) -> int | None:
    found = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
    )

    def _cb(hwnd, _):
        p = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and ctypes.windll.user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    ctypes.windll.user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return found[0] if found else None


def _get_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    r = ctypes.wintypes.RECT()
    if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return r.left, r.top, r.right, r.bottom
    return None


# ── Overlay ───────────────────────────────────────────────────────────────────

class ScrcpyOverlay:
    """
    Pill flotante centrado en la parte superior de la ventana scrcpy.
    Diseño: [ 📷 ] (sin switch)
    Pegado a la barra superior, desaparece si se minimiza la ventana.
    """

    def __init__(self, root: ctk.CTk, pid: int, on_capture):
        self.root       = root
        self.pid        = pid
        self.on_capture = on_capture
        self._running   = True
        self.win        = None
        
        # Cargar icono de camara local
        self.img_camera = _load_local_image("camera.png", (16, 16))

        threading.Thread(target=self._wait_and_show, daemon=True).start()

    def _wait_and_show(self):
        import time
        for _ in range(30):          # máx 15 s
            if not self._running:
                return
            hwnd = _find_window_by_pid(self.pid)
            if hwnd:
                self.root.after(0, lambda: self._build(hwnd))
                return
            time.sleep(0.5)
        logger.warning("ScrcpyOverlay: ventana scrcpy no detectada tras 15 s.")

    def _build(self, hwnd):
        self.hwnd = hwnd
        import tkinter as tk
        try:
            self.win = tk.Toplevel(self.root)
            self.win.withdraw()
            self.win.overrideredirect(True)
            self.win.attributes("-topmost", True)
            self.win.attributes("-alpha", 0.95)
            self.win.configure(bg=_KEY)
            self.win.wm_attributes("-transparentcolor", _KEY)
            
            # Oculto al inicio hasta calcular coords
            self.win.geometry("+-1000+-1000")

            pill = ctk.CTkFrame(
                self.win,
                fg_color="transparent", # Contenedor invisible
                corner_radius=0,
                border_width=0,
            )
            pill.pack()

            cam_btn = ctk.CTkButton(
                pill,
                text="",
                image=self.img_camera,
                command=self._do_capture,
                width=32, height=32, corner_radius=0, # Exactamente 32x32, recto
                fg_color="transparent", 
                hover_color="#334155",
                border_width=0,
            )
            cam_btn.pack()

            # Efecto hover ligero
            self.win.bind("<Enter>", lambda _: self.win.wm_attributes("-alpha", 1.0))
            self.win.bind("<Leave>", lambda _: self.win.wm_attributes("-alpha", 0.95))

            self._track_window()

        except Exception as e:
            logger.error(f"ScrcpyOverlay._build: {e}")

    def _do_capture(self):
        # La configuración "con marco" ahora se lee automáticamente desde la interfaz principal de DroidCast.
        self.on_capture()

    def _track_window(self):
        """Se ejecuta a 60FPS para mantener el overlay pegado a la ventana y ocultarlo si minimiza."""
        if not self._running:
            return
            
        from app.core.scrcpy import scrcpy_process
        if scrcpy_process is None or scrcpy_process.poll() is not None:
            self.root.after(0, self.destroy)
            return

        if not self.win or not self.win.winfo_exists():
            return

        user32 = ctypes.windll.user32
        fg_hwnd = user32.GetForegroundWindow()
        
        try:
            my_hwnd = int(self.win.wm_frame(), 16)
        except:
            my_hwnd = 0

        # Solo la escondemos si Scrcpy está minimizada a la barra de tareas
        if user32.IsIconic(self.hwnd):
            if self.win.winfo_viewable():
                self.win.withdraw()
        else:
            if not self.win.winfo_viewable():
                self.win.deiconify()
                
            # Z-Order Dinámico
            if fg_hwnd == self.hwnd or fg_hwnd == my_hwnd:
                self.win.attributes("-topmost", True)
            else:
                self.win.attributes("-topmost", False)
            
            rect = _get_rect(self.hwnd)
            if rect:
                left, top, right, bottom = rect
                
                # Si está maximizada, Windows le suma ~8px invisibles a los bordes
                if user32.IsZoomed(self.hwnd):
                    top += 8
                    right -= 8
                
                # Botones de Windows miden ~138px. Botón mide 32px -> 170px.
                x = right - 172
                y = top  
                
                self.win.geometry(f"+{x}+{y}")
        
        self.win.after(16, self._track_window)  # ~60 fps

    def destroy(self):
        self._running = False
        try:
            if self.win and self.win.winfo_exists():
                self.win.destroy()
        except Exception:
            pass
        self.win = None