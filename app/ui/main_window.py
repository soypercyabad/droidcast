# ══════════════════════════════════════════════════════════════════════════════
# app/ui/main_window.py — Construcción de la UI principal (Refactorizado a OOP)
# ══════════════════════════════════════════════════════════════════════════════

import logging
import os
import threading
import atexit
import webbrowser
import tkinter as tk
from tkinter import filedialog, ttk
from io import BytesIO

import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import requests

from app.theme import Theme
from app import config
from app.core.adb import validate_ip, validate_port
from app.core.scrcpy import run_scrcpy, close_processes
from app.core import device as _device
from app.core import screenshot as _screenshot
from app.core import apk_manager
from app.ui.bootstrap_switch import BootstrapSwitch

logger = logging.getLogger(__name__)

MAX_TREEVIEW_DEPTH = 10


# ── FUNCIONES AUXILIARES ──────────────────────────────────────────────────────

def _open_github():
    webbrowser.open("https://github.com/soypercyabad")


def _download_image_safe(url, size):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        return img.resize(size, Image.LANCZOS) if size else img
    except Exception:
        return None


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


class MainWindow:
    """Clase principal que encapsula la UI de DroidCast."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self.ui = {}
        
        # Iconos por defecto (fallback)
        self.tree_folder_icon = self._create_icon(18, "#FFA726")
        self.tree_apk_icon = self._create_icon(18, "#66BB6A")
        
        # Cargar iconos locales
        self.img_apk = _load_local_image("apk.png", (24, 24))
        self.img_code = _load_local_image("code.png", (24, 24))
        self.img_cast = _load_local_image("cast-screen.png", (24, 24))
        self.img_folder = _load_local_image("folder.png", (18, 18))
        self.img_refresh = _load_local_image("refresh.png", (18,18))
        
        self.setup_window()
        self.build_ui()
        
        # Cargar config guardada
        default_path, default_ip, default_port, default_phone_frame = config.load()
        if default_ip:
            self.ui["ip_entry"].insert(0, default_ip)
        if default_port:
            self.ui["port_entry"].insert(0, default_port)
        if default_path:
            self.ui["root_path_var"].set(default_path)
            self._update_path_display(default_path)
            
        if default_phone_frame:
            self.ui["use_frame_switch"].select()
        else:
            self.ui["use_frame_switch"].deselect()
            
        self.setup_bindings()
        
        atexit.register(close_processes)
        
        if default_path and os.path.isdir(default_path):
            self.update_treeview(default_path)
            
        threading.Thread(target=self._load_images_async, daemon=True).start()
        self.periodic_check()

    def _create_icon(self, size, color):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(img).rounded_rectangle((1, 1, size-1, size-1), 3, fill=color)
        return ImageTk.PhotoImage(img)

    def setup_window(self):
        self.root.title("DroidCast")
        self.root.geometry("850x480")
        self.root.resizable(False, False)
        self.root.configure(fg_color=Theme.BG)
        
        try:
            icon_path = os.path.join(config.ASSETS_DIR, "assets", "robot.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    # ── CONSTRUCCIÓN DE LA UI ──────────────────────────────────────────────────

    def build_ui(self):
        self._build_banner()
        
        # ── main container: 2 columnas de peso igual ──────────────────────────
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        # Una sola fila que se estira — esto garantiza misma altura para ambas columnas
        main_container.rowconfigure(0, weight=1)
        
        left_col = ctk.CTkFrame(main_container, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left_col.rowconfigure(0, weight=0)   # device card: tamaño natural
        left_col.rowconfigure(1, weight=1)   # wifi card: se estira para igualar
        
        self._build_device_card(left_col)
        self._build_wifi_card(left_col)
        
        right_col = ctk.CTkFrame(main_container, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right_col.rowconfigure(0, weight=1)  # apk card llena toda la altura
        
        self._build_apk_card(right_col)
        self._build_footer()

    def _build_banner(self):
        banner_path = os.path.join(config.ASSETS_DIR, "assets", "banner.png")
        target_w, target_h = 850, 108
        try:
            banner_img = Image.open(banner_path)
            ratio = max(target_w / banner_img.width, target_h / banner_img.height)
            new_w = int(banner_img.width * ratio)
            new_h = int(banner_img.height * ratio)
            banner_img = banner_img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - target_w) // 2
            top  = (new_h - target_h) // 2
            banner_img = banner_img.crop((left, top, left + target_w, top + target_h))
        except Exception:
            banner_img = Image.new("RGB", (target_w, target_h), "#7C3AED")
        
        self.ui["cover_photo"] = ctk.CTkImage(
            light_image=banner_img, dark_image=banner_img,
            size=(target_w, target_h)
        )
        ctk.CTkLabel(self.root, image=self.ui["cover_photo"], text="").pack(fill="x")

    def _build_device_card(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=Theme.CARD, corner_radius=12,
            border_width=1, border_color=Theme.BORDER
        )
        # grid en fila 0 — altura natural
        card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        
        # ── Header ──
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))
        
        ctk.CTkFrame(header, fg_color=Theme.PURPLE, width=4, height=16, corner_radius=2).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(header, text="DISPOSITIVO", font=(Theme.FONT, 13, "bold"), text_color=Theme.TEXT_SEC).pack(side="left")
        self._create_help_btn(header).pack(side="left", padx=(8, 0))
        
        # ── Content ── (orden importante: right primero, luego left)
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=14, pady=(2, 12))

        # ── Botones lado derecho (se empaca primero — regla del pack manager) ──
        btns_frame = ctk.CTkFrame(content, fg_color="transparent")
        btns_frame.pack(side="right")

        # Switch Marco (título + switch apilados)
        switch_container = ctk.CTkFrame(btns_frame, fg_color="transparent")
        switch_container.pack(side="left", padx=(0, 14))

        ctk.CTkLabel(
            switch_container, text="Marco",
            font=(Theme.FONT, 11, "bold"), text_color=Theme.TEXT_SEC
        ).pack(pady=(0, 2))

        self.ui["use_frame_switch"] = BootstrapSwitch(
            switch_container,
            width=28,
            height=16,
            fg_color="#CBD5E1",
            progress_color=Theme.GREEN,
            bg_color=Theme.CARD,
            command=self._save_config
        )
        self.ui["use_frame_switch"].pack(pady=(0, 8))

        # btn Android (APK)
        self.ui["btn_android"] = ctk.CTkButton(
            btns_frame, text="", image=self.img_apk,
            width=42, height=42, corner_radius=12,
            fg_color=Theme.NAVY, hover_color=Theme.NAVY_HOVER,
            state="disabled"
        )
        self.ui["btn_android"].pack(side="left", padx=(0, 8))

        # btn Code (logs de red)
        self.ui["btn_code"] = ctk.CTkButton(
            btns_frame, text="", image=self.img_code,
            width=42, height=42, corner_radius=12,
            fg_color=Theme.INDIGO, hover_color=Theme.INDIGO_HOVER,
            command=self.open_log_viewer
        )
        self.ui["btn_code"].pack(side="left", padx=(0, 8))

        # btn Cast (screen mirror)
        self.ui["btn_cast"] = ctk.CTkButton(
            btns_frame, text="", image=self.img_cast,
            width=42, height=42, corner_radius=12,
            fg_color=Theme.PURPLE, hover_color=Theme.PURPLE_HOVER,
            command=self._start_cast
        )
        self.ui["btn_cast"].pack(side="left")

        # ── Separador vertical (empacado derecha, DESPUÉS del btns_frame) ──
        ctk.CTkFrame(
            content, fg_color="#CBD5E1", width=2, height=54
        ).pack(side="right", fill="y", padx=(8, 8), pady=2)

        # ── Info lado izquierdo ──
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="y")

        status_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        status_row.pack(anchor="w")

        self.ui["status_indicator"] = ctk.CTkFrame(
            status_row, fg_color=Theme.RED, width=10, height=10, corner_radius=5
        )
        self.ui["status_indicator"].pack(side="left", padx=(0, 7), pady=4)

        self.ui["status_label"] = ctk.CTkLabel(
            status_row, text="Dispositivo desconectado",
            font=(Theme.FONT, 13, "bold"), text_color=Theme.RED
        )
        self.ui["status_label"].pack(side="left")

        self.ui["device_info_label"] = ctk.CTkLabel(
            info_frame, text="Sin dispositivo detectado",
            font=(Theme.FONT, 12), text_color=Theme.TEXT_MUTED
        )
        self.ui["device_info_label"].pack(anchor="w", pady=(2, 0))


    def _build_wifi_card(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=Theme.CARD, corner_radius=12,
            border_width=1, border_color=Theme.BORDER
        )
        # grid fila 1 con sticky="nsew" → se estira para igualar altura columna derecha
        card.grid(row=1, column=0, sticky="nsew")
        
        # ── Header ──
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 6))
        
        ctk.CTkFrame(header, fg_color=Theme.BLUE, width=4, height=16, corner_radius=2).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(header, text="CONEXIÓN WI-FI", font=(Theme.FONT, 13, "bold"), text_color=Theme.TEXT_SEC).pack(side="left")
        self._create_help_btn(header).pack(side="left", padx=(8, 0))
        
        # ── Inputs IP + Puerto + Conectar ──
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(0, 6))
        grid.columnconfigure(0, weight=3)
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(2, weight=0)
        
        ctk.CTkLabel(grid, text="IP Address", font=(Theme.FONT, 12, "bold"), text_color=Theme.TEXT_SEC).grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        ctk.CTkLabel(grid, text="Puerto", font=(Theme.FONT, 12, "bold"), text_color=Theme.TEXT_SEC).grid(
            row=0, column=1, sticky="w", padx=(0, 6)
        )
        
        self.ui["ip_entry"] = ctk.CTkEntry(
            grid, placeholder_text="192.168.1.100",
            height=36, corner_radius=8,
            border_color=Theme.BORDER, border_width=2,
            fg_color=Theme.INPUT_BG, text_color=Theme.TEXT,
            font=(Theme.FONT, 13)
        )
        self.ui["ip_entry"].grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))
        
        self.ui["port_entry"] = ctk.CTkEntry(
            grid, placeholder_text="5555",
            height=36, corner_radius=8,
            border_color=Theme.BORDER, border_width=2,
            fg_color=Theme.INPUT_BG, text_color=Theme.TEXT,
            font=(Theme.FONT, 13), width=70
        )
        self.ui["port_entry"].grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(2, 0))
        
        self.ui["connect_btn"] = ctk.CTkButton(
            grid, text="Conectar", command=self.connect_device,
            width=110, height=36, corner_radius=8,
            fg_color=Theme.BLUE, hover_color=Theme.BLUE_HOVER,
            font=(Theme.FONT, 13, "bold"), text_color=Theme.WHITE
        )
        self.ui["connect_btn"].grid(row=1, column=2, pady=(2, 0))
        
        # ── Hint box ──
        hint = ctk.CTkFrame(
            card, fg_color=Theme.HINT_BG,
            corner_radius=8, border_width=1, border_color=Theme.HINT_BORDER
        )
        hint.pack(fill="x", padx=14, pady=(6, 14))
        ctk.CTkLabel(
            hint,
            text="ℹ Primera vez? Conecte por USB y acepte la autorización de depuración",
            font=(Theme.FONT, 11), text_color=Theme.HINT_TEXT,
            wraplength=460, justify="left"
        ).pack(padx=10, pady=7, anchor="w")

    def _build_apk_card(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=Theme.CARD, corner_radius=12,
            border_width=1, border_color=Theme.BORDER
        )
        # sticky="nsew" + rowconfigure weight=1 en el parent → misma altura que columna izquierda
        card.grid(row=0, column=0, sticky="nsew")
        card.rowconfigure(3, weight=1)   # la fila del tree se estira
        card.columnconfigure(0, weight=1)
        
        # ── Header ──
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 6))
        
        ctk.CTkFrame(header, fg_color=Theme.TEAL, width=4, height=16, corner_radius=2).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(header, text="INSTALAR APK", font=(Theme.FONT, 13, "bold"), text_color=Theme.TEXT).pack(side="left")
        self._create_help_btn(header).pack(side="left", padx=(8, 0))
        
        # ── Path Row ──
        path_row = ctk.CTkFrame(card, fg_color="transparent")
        path_row.pack(fill="x", padx=14, pady=(0, 6))
        
        self.ui["root_path_var"] = tk.StringVar()
        self.ui["path_display"] = ctk.CTkLabel(
            path_row, text="Seleccionar carpeta...",
            font=(Theme.FONT, 12), text_color=Theme.TEXT_SEC, anchor="w"
        )
        self.ui["path_display"].pack(side="left", fill="x", expand=True)
        
        ctk.CTkButton(
            path_row,
            text="📂" if not self.img_folder else "",
            image=self.img_folder,
            command=self.select_root_path,
            width=38, height=38, corner_radius=8,
            fg_color=Theme.BTN_LIGHT, hover_color=Theme.BTN_LIGHT_HVR,
            text_color=Theme.TEXT_SEC, border_width=0
        ).pack(side="left", padx=(4, 8))
        
        ctk.CTkButton(
            path_row, text="Instalar APK", command=self.install_apk,
            width=110, height=38, corner_radius=8,
            text_color=Theme.WHITE,
            fg_color=Theme.TEAL, hover_color=Theme.TEAL_HOVER,
            font=(Theme.FONT, 13, "bold")
        ).pack(side="right")
        
        # ── Tree header ──
        tree_hdr = ctk.CTkFrame(card, fg_color="transparent")
        tree_hdr.pack(fill="x", padx=14, pady=(2, 4))
        
        ctk.CTkButton(
            tree_hdr,
            text="↻" if not self.img_refresh else "",
            image=self.img_refresh,
            command=lambda: self.update_treeview(self.ui["root_path_var"].get()),
            width=22, height=32, corner_radius=6,
            fg_color=Theme.BTN_LIGHT, hover_color=Theme.BTN_LIGHT_HVR,
            text_color=Theme.TEXT_SEC, border_width=0
        ).pack(side="left")
        
        ctk.CTkLabel(
            tree_hdr, text="Directorio de Apks",
            font=(Theme.FONT, 12, "bold"), text_color=Theme.TEXT_SEC
        ).pack(side="left", padx=8)
        
        # ── Tree container ──
        tree_border = ctk.CTkFrame(
            card, fg_color=Theme.BG, corner_radius=8,
            border_width=1, border_color=Theme.BORDER, height=1
        )
        tree_border.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        tree_border.pack_propagate(False)
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Card.Treeview",
            background="white", foreground=Theme.TEXT,
            fieldbackground="white", borderwidth=0,
            font=(Theme.FONT, 10), rowheight=26
        )
        style.configure(
            "Card.Treeview.Heading",
            background=Theme.BG, foreground=Theme.TEXT_SEC,
            font=(Theme.FONT, 12, "bold"), borderwidth=0, relief="flat"
        )
        style.map(
            "Card.Treeview",
            background=[("selected", Theme.TREE_SELECT_BG)],
            foreground=[("selected", Theme.TREE_SELECT_FG)]
        )
        style.configure(
            "Modern.Vertical.TScrollbar",
            background="#C4C9D0", troughcolor="#F0F2F5",
            borderwidth=0, width=6, arrowsize=0, relief="flat"
        )
        style.map(
            "Modern.Vertical.TScrollbar",
            background=[("active", "#9CA3AF"), ("!active", "#C4C9D0")]
        )
        style.layout(
            "Modern.Vertical.TScrollbar",
            [("Vertical.Scrollbar.trough", {
                "sticky": "ns",
                "children": [("Vertical.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})]
            })]
        )
        
        tree_inner = tk.Frame(tree_border, bg="white", padx=4, pady=4)
        tree_inner.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.ui["tree"] = ttk.Treeview(tree_inner, height=10, style="Card.Treeview", show="tree")
        self.ui["tree"].heading("#0", text="Directorio", anchor="w")
        
        scroll = ttk.Scrollbar(
            tree_inner, orient="vertical",
            command=self.ui["tree"].yview,
            style="Modern.Vertical.TScrollbar"
        )
        self.ui["tree"].configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.ui["tree"].pack(fill="both", expand=True, side="left")

    def _build_footer(self):
        footer = ctk.CTkFrame(self.root, fg_color="transparent", height=40)
        footer.pack(fill="x", pady=(4, 6))
        ctk.CTkFrame(footer, fg_color=Theme.BORDER, height=1).pack(fill="x", padx=30, pady=(0, 6))

        # Contenedor centrado
        center = ctk.CTkFrame(footer, fg_color="transparent")
        center.pack(anchor="center")

        credits = ctk.CTkLabel(
            center, text="Desarrollado por @soypercyabad",
            font=(Theme.FONT, 11), text_color=Theme.TEXT_MUTED, cursor="hand2"
        )
        credits.pack(side="left")
        credits.bind("<Button-1>", lambda e: _open_github())
        credits.bind("<Enter>", lambda e: credits.configure(text_color=Theme.BLUE))
        credits.bind("<Leave>", lambda e: credits.configure(text_color=Theme.TEXT_MUTED))

        ctk.CTkLabel(
            center, text="  v2.0",
            font=(Theme.FONT, 10), text_color=Theme.TEXT_MUTED
        ).pack(side="left")

    def open_log_viewer(self):
        from app.ui import log_viewer
        log_viewer.show(self.root)

    def _create_help_btn(self, parent):
        from app.ui import help_window
        return ctk.CTkButton(
            parent, text="?", command=lambda: help_window.show(self.root),
            width=20, height=20, corner_radius=10,
            fg_color="#F1F5F9", hover_color=Theme.BORDER,
            text_color=Theme.TEXT_SEC, font=(Theme.FONT, 11, "bold"),
        )

    # ── LOGICA Y CALLBACKS ──────────────────────────────────────────────────

    def setup_bindings(self):
        self.ui["ip_entry"].bind("<FocusOut>", self.on_field_change)
        self.ui["port_entry"].bind("<FocusOut>", self.on_field_change)

    def on_field_change(self, *args):
        self._save_config()

    def _save_config(self):
        """Guarda la configuración actual (path, ip, port, switch de marco)."""
        config.save(
            self.ui["root_path_var"].get(), 
            self.ui["ip_entry"].get(), 
            self.ui["port_entry"].get(),
            self.ui["use_frame_switch"].get() == 1
        )

    def select_root_path(self):
        path = filedialog.askdirectory()
        if path:
            self.ui["root_path_var"].set(path)
            self._update_path_display(path)
            self._save_config()
            self.update_treeview(path)

    def _update_path_display(self, path):
        display = path if len(path) < 30 else "..." + path[-27:]
        self.ui["path_display"].configure(text=display)

    def _start_cast(self):
        def _on_scrcpy_started(pid: int):
            from app.ui.scrcpy_overlay import ScrcpyOverlay
            ScrcpyOverlay(self.root, pid, self.do_clipboard_capture)
        run_scrcpy(self.root, on_started=_on_scrcpy_started)

    def do_clipboard_capture(self, *args):
        # Lee la configuración directamente del switch del usuario
        use_frame = bool(self.ui.get("use_frame_switch") and self.ui["use_frame_switch"].get() == 1)
        
        def _clip():
            success, error = _screenshot.capture_to_clipboard(with_phone_frame=use_frame)
            if success:
                lbl = " (con marco)" if use_frame else ""
                self.root.after(0, lambda: self._show_toast("Captura exitosa", "success"))
            else:
                self.root.after(0, lambda _e=error: self._show_toast("Error al capturar", _e, "error"))
        threading.Thread(target=_clip, daemon=True).start()

    def _show_toast(self, title: str, msg: str, type: str = "success"):
        try:
            from app.ui.toast import ToastManager
            ToastManager.show(self.root, title, msg, type)
        except Exception as e:
            logger.error(f"Error showing toast: {e}")

    def update_treeview(self, path):
        if not path or not os.path.isdir(path):
            return
        for i in self.ui["tree"].get_children():
            self.ui["tree"].delete(i)
        self._insert_items("", path, 0)

    def _insert_items(self, parent, fullpath, depth):
        if depth > MAX_TREEVIEW_DEPTH:
            return
        try:
            items = sorted(os.listdir(fullpath))
        except (PermissionError, OSError):
            return
        for item in items:
            path = os.path.join(fullpath, item)
            try:
                if os.path.islink(path): continue
                if os.path.isdir(path):
                    node = self.ui["tree"].insert(parent, "end", text=item, open=False, image=self.tree_folder_icon)
                    self._insert_items(node, path, depth + 1)
                elif item.lower().endswith(".apk"):
                    self.ui["tree"].insert(parent, "end", text=item, image=self.tree_apk_icon)
            except Exception:
                continue

    def install_apk(self):
        from app.ui.dialogs import ProgressOverlay, ResultDialog
        selected = self.ui["tree"].selection()
        if not selected:
            ResultDialog(self.root, "Sin selección", "Seleccione un archivo APK del directorio.", "warning")
            return
        name = self.ui["tree"].item(selected, "text")
        if not name.lower().endswith(".apk"):
            ResultDialog(self.root, "No es APK", "Seleccione un archivo .apk, no una carpeta.", "warning")
            return
            
        parent = self.ui["tree"].parent(selected)
        full = name
        while parent:
            full = os.path.join(self.ui["tree"].item(parent, "text"), full)
            parent = self.ui["tree"].parent(parent)
        full = os.path.join(self.ui["root_path_var"].get(), full)
        
        if not os.path.exists(full):
            ResultDialog(self.root, "Archivo no encontrado", "El archivo APK no existe.", "error", full)
            return
            
        overlay = ProgressOverlay(self.root, "Instalando APK...")
        overlay.update_status(f"Transfiriendo {name}...")
        overlay.start_indeterminate()
        overlay.progress.configure(progress_color=Theme.TEAL)

        def _install():
            import time
            result_code, output = apk_manager.install(full)
            if result_code == apk_manager.RESULT_SUCCESS:
                self.root.after(0, overlay.finish_progress)
                time.sleep(0.4)
                self.root.after(0, overlay.close)
                self.root.after(10, lambda: ResultDialog(self.root, "Instalación exitosa", f"{name} se instaló correctamente en el dispositivo.", "success"))
            elif result_code == apk_manager.RESULT_USER_RESTRICTED:
                self.root.after(0, overlay.close)
                self.root.after(10, lambda: ResultDialog(self.root, "Instalación bloqueada", "El dispositivo requiere autorización para instalar.", "warning", "Pasos:\n1. Ajustes → Opciones de desarrollador\n2. Active 'Instalar vía USB'\n3. Acepte el diálogo en el dispositivo"))
            elif result_code == apk_manager.RESULT_INSUFFICIENT_STORAGE:
                self.root.after(0, overlay.close)
                self.root.after(10, lambda: ResultDialog(self.root, "Sin espacio", "No hay espacio suficiente en el dispositivo.", "error", "Libere espacio e intente nuevamente."))
            elif result_code == apk_manager.RESULT_TIMEOUT:
                self.root.after(0, overlay.close)
                self.root.after(10, lambda: ResultDialog(self.root, "Tiempo agotado", f"La instalación de {name} tardó demasiado.", "warning", "Conexión Wi-Fi lenta. Intente por USB."))
            else:
                self.root.after(0, overlay.close)
                self.root.after(10, lambda _o=output: ResultDialog(self.root, "Error al instalar", f"No se pudo instalar {name}.", "error", _o))
                
        threading.Thread(target=_install, daemon=True).start()

    def check_device_connection(self):
        def _check():
            connected = _device.check_connection()
            self.root.after(0, lambda: self.update_connection_status(connected))
        threading.Thread(target=_check, daemon=True).start()

    def disconnect_device(self):
        from app.ui.dialogs import ConfirmDialog
        confirm = ConfirmDialog(self.root, "Desconectar", "¿Está seguro de finalizar la conexión ADB?")
        if confirm.result:
            _device.disconnect()
            self.update_connection_status(False)

    def update_connection_status(self, connected):
        if connected:
            self.ui["status_indicator"].configure(fg_color=Theme.GREEN)
            self.ui["status_label"].configure(text="Dispositivo conectado", text_color=Theme.GREEN)
            threading.Thread(target=self._update_device_info, daemon=True).start()
            self.ui["connect_btn"].configure(text="Desconectar", fg_color=Theme.RED, hover_color=Theme.RED_HOVER, text_color=Theme.WHITE, command=self.disconnect_device)
        else:
            self.ui["status_indicator"].configure(fg_color=Theme.RED)
            self.ui["status_label"].configure(text="Dispositivo desconectado", text_color=Theme.RED)
            self.ui["device_info_label"].configure(text="Sin dispositivo detectado")
            self.ui["connect_btn"].configure(text="Conectar", fg_color=Theme.BLUE, hover_color=Theme.BLUE_HOVER, text_color=Theme.WHITE, command=self.connect_device)

    def _update_device_info(self):
        info = _device.get_device_info()
        if info:
            text = f"{info['model']}  ·  Android {info['version']}"
            if info.get('sdk'):
                text += f"  (API {info['sdk']})"
            self.root.after(0, lambda: self.ui["device_info_label"].configure(text=text))

    def periodic_check(self):
        self.check_device_connection()
        self.root.after(15000, self.periodic_check)

    def connect_device(self):
        from app.ui.dialogs import ProgressOverlay, ResultDialog
        ip = self.ui["ip_entry"].get().strip()
        port = self.ui["port_entry"].get().strip()

        if not validate_ip(ip):
            ResultDialog(self.root, "IP inválida", "Ingrese una IP válida.\nEjemplo: 192.168.1.100", "warning")
            return
        if not validate_port(port):
            ResultDialog(self.root, "Puerto inválido", "Ingrese un puerto válido (1-65535).\nEjemplo: 5555", "warning")
            return

        overlay = ProgressOverlay(self.root, "Conectando...")
        overlay.update_status(f"Iniciando conexión a {ip}:{port}...")
        overlay.start_indeterminate()
        overlay.progress.configure(progress_color=Theme.BLUE)

        def _connect():
            overlay.update_status(f"Conectando a {ip}:{port}...")
            success, status_key, message = _device.connect(ip, port)
            self.root.after(0, overlay.close)
            if success:
                self._save_config()
                self.root.after(0, lambda: self.update_connection_status(True))
                title = "Conexión exitosa" if status_key == "connected" else "Ya conectado"
                dtype = "success" if status_key == "connected" else "info"
                self.root.after(10, lambda _m=message: ResultDialog(self.root, title, _m, dtype))
            else:
                self.root.after(0, lambda: self.update_connection_status(False))
                self.root.after(10, lambda _m=message: ResultDialog(self.root, "Error de conexión", "No se pudo conectar al dispositivo.", "error", _m))
        threading.Thread(target=_connect, daemon=True).start()

    def _load_images_async(self):
        img_folder_pil = _download_image_safe("https://raw.githubusercontent.com/soypercyabad/images-projects/main/Carpeta.png", (18, 18))
        if img_folder_pil:
            self.tree_folder_icon = ImageTk.PhotoImage(img_folder_pil)
        
        img_apk_pil = _download_image_safe("https://raw.githubusercontent.com/soypercyabad/images-projects/main/android.png", (18, 18))
        if img_apk_pil:
            self.tree_apk_icon = ImageTk.PhotoImage(img_apk_pil)
            
        p = self.ui["root_path_var"].get()
        if p and os.path.isdir(p):
            self.root.after(0, lambda: self.update_treeview(p))


# ── PUNTO DE ENTRADA ──────────────────────────────────────────────────────────

def start():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = MainWindow(root)
    root.mainloop()
