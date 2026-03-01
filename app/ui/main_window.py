# ══════════════════════════════════════════════════════════════════════════════
# app/ui/main_window.py — Construcción de la UI principal
# ══════════════════════════════════════════════════════════════════════════════

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
from app.core.adb import run_adb, validate_ip, validate_port
from app.core.scrcpy import run_scrcpy, close_processes

import logging

logger = logging.getLogger(__name__)

MAX_TREEVIEW_DEPTH = 10


# ══════════════════════════════════════════════════════════════════════════════
# ── FUNCIONES AUXILIARES ──────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _open_github():
    webbrowser.open("https://github.com/soypercyabad")


def _create_icon(size, color):
    """Crea un icono cuadrado redondeado con color sólido."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((1, 1, size-1, size-1), 3, fill=color)
    return ImageTk.PhotoImage(img)


def _download_image_safe(url, size):
    """Descarga una imagen de forma segura. Retorna None si falla."""
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content))
        return img.resize(size, Image.LANCZOS) if size else img
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ── FUNCIÓN DE ARRANQUE ───────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def start():
    """Construye la UI y arranca el mainloop."""

    # ── Logging ──────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    # ══════════════════════════════════════════════════════════════════════
    # ── VENTANA PRINCIPAL ─────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    root = ctk.CTk()
    root.title("DroidCast")
    root.geometry("820x460")
    root.resizable(False, False)
    root.configure(fg_color=Theme.BG)

    try:
        icon_path = os.path.join(config.ASSETS_DIR, "assets", "robot.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    # ── Estado compartido ────────────────────────────────────────────────
    # Usamos un diccionario para compartir widgets entre funciones anidadas
    ui = {}

    # ══════════════════════════════════════════════════════════════════════
    # ── CALLBACKS ─────────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    def on_field_change(*_args):
        config.save(ui["root_path_var"].get(), ui["ip_entry"].get(), ui["port_entry"].get())

    def select_root_path():
        path = filedialog.askdirectory()
        if path:
            ui["root_path_var"].set(path)
            ui["path_display"].configure(
                text=path if len(path) < 30 else "..." + path[-27:])
            config.save(path, ui["ip_entry"].get(), ui["port_entry"].get())
            update_treeview(path)

    def install_apk():
        from app.ui.dialogs import ProgressOverlay, ResultDialog

        selected = ui["tree"].selection()
        if not selected:
            ResultDialog(root, "Sin selección",
                "Seleccione un archivo APK del directorio.", "warning")
            return
        name = ui["tree"].item(selected, "text")
        if not name.lower().endswith(".apk"):
            ResultDialog(root, "No es APK",
                "Seleccione un archivo .apk, no una carpeta.", "warning")
            return

        parent = ui["tree"].parent(selected)
        full = name
        while parent:
            full = os.path.join(ui["tree"].item(parent, "text"), full)
            parent = ui["tree"].parent(parent)
        full = os.path.join(ui["root_path_var"].get(), full)

        if not os.path.exists(full):
            ResultDialog(root, "Archivo no encontrado",
                "El archivo APK no existe en la ruta especificada.",
                "error", full)
            return

        overlay = ProgressOverlay(root, "Instalando APK...")
        overlay.update_status(f"Transfiriendo {name}...")
        overlay.start_indeterminate()
        overlay.progress.configure(progress_color=Theme.TEAL)

        def _install():
            try:
                stdout, stderr, _ = run_adb(["install", "-r", full])
                output = f"{stdout}\n{stderr}"
                if "Success" in stdout:
                    root.after(0, lambda: overlay.finish_progress())
                    import time; time.sleep(0.4)
                    root.after(0, overlay.close)
                    root.after(10, lambda: ResultDialog(root,
                        "Instalación exitosa",
                        f"{name} se instaló correctamente en el dispositivo.",
                        "success"))
                elif "INSTALL_FAILED_USER_RESTRICTED" in output:
                    root.after(0, overlay.close)
                    root.after(10, lambda: ResultDialog(root,
                        "Instalación bloqueada",
                        "El dispositivo requiere autorización para instalar.",
                        "warning",
                        "Pasos:\n"
                        "1. Vaya a Ajustes → Opciones de desarrollador\n"
                        "2. Active 'Instalar vía USB'\n"
                        "3. Acepte el diálogo en la pantalla del dispositivo"))
                elif "INSTALL_FAILED_INSUFFICIENT_STORAGE" in output:
                    root.after(0, overlay.close)
                    root.after(10, lambda: ResultDialog(root,
                        "Sin espacio",
                        "No hay espacio suficiente en el dispositivo.",
                        "error",
                        "Libere espacio en su dispositivo e intente nuevamente."))
                elif "Tiempo de espera agotado" in output:
                    root.after(0, overlay.close)
                    root.after(10, lambda: ResultDialog(root,
                        "Tiempo agotado",
                        f"La instalación de {name} tardó demasiado.",
                        "warning",
                        "Esto puede ocurrir por conexión Wi-Fi lenta.\n"
                        "Intente conectar el dispositivo por USB."))
                else:
                    root.after(0, overlay.close)
                    root.after(10, lambda: ResultDialog(root,
                        "Error al instalar",
                        f"No se pudo instalar {name}.",
                        "error", output.strip()))
            except Exception as e:
                root.after(0, overlay.close)
                root.after(10, lambda: ResultDialog(root,
                    "Error", str(e), "error"))
        threading.Thread(target=_install, daemon=True).start()

    def update_treeview(path):
        if not path or not os.path.isdir(path):
            return
        for i in ui["tree"].get_children():
            ui["tree"].delete(i)
        _insert_items("", path, 0)

    def _insert_items(parent, fullpath, depth):
        if depth > MAX_TREEVIEW_DEPTH:
            return
        try:
            items = sorted(os.listdir(fullpath))
        except (PermissionError, OSError):
            return
        for item in items:
            path = os.path.join(fullpath, item)
            try:
                if os.path.islink(path):
                    continue
                if os.path.isdir(path):
                    node = ui["tree"].insert(parent, "end", text=item, open=False,
                                             image=ui["folder_icon"])
                    _insert_items(node, path, depth + 1)
                elif item.lower().endswith(".apk"):
                    ui["tree"].insert(parent, "end", text=item, image=ui["apk_icon"])
            except Exception:
                continue

    # ── Conexión ADB ─────────────────────────────────────────────────────

    def check_device_connection():
        def _check():
            try:
                stdout, _, _ = run_adb(["devices"])
                lines = stdout.splitlines()
                connected = any("device" in l and "offline" not in l for l in lines[1:])
                root.after(0, lambda: update_connection_status(connected))
            except Exception:
                root.after(0, lambda: update_connection_status(False))
        threading.Thread(target=_check, daemon=True).start()

    def disconnect_device():
        from app.ui.dialogs import ConfirmDialog
        confirm = ConfirmDialog(root, "Desconectar",
                                "¿Está seguro de finalizar la conexión ADB?")
        if confirm.result:
            try:
                run_adb(["disconnect"])
            except Exception:
                pass
            update_connection_status(False)

    def update_connection_status(connected):
        if connected:
            ui["status_indicator"].configure(fg_color=Theme.GREEN)
            ui["status_label"].configure(text="Dispositivo conectado",
                                         text_color=Theme.GREEN)
            threading.Thread(target=_update_device_info, daemon=True).start()
            ui["connect_btn"].configure(
                text="Desconectar", fg_color=Theme.RED, hover_color="#B91C1C",
                command=disconnect_device)
        else:
            ui["status_indicator"].configure(fg_color=Theme.RED)
            ui["status_label"].configure(text="Dispositivo desconectado",
                                         text_color=Theme.RED)
            ui["device_info_label"].configure(text="Sin dispositivo detectado")
            ui["connect_btn"].configure(
                text="Conectar", fg_color=Theme.BLUE, hover_color=Theme.BLUE_HOVER,
                command=connect_device)

    def _update_device_info():
        try:
            model, _, _ = run_adb(["shell", "getprop", "ro.product.model"])
            version, _, _ = run_adb(["shell", "getprop", "ro.build.version.release"])
            sdk, _, _ = run_adb(["shell", "getprop", "ro.build.version.sdk"])
            m = model.strip() or "Desconocido"
            v = version.strip() or "?"
            s = sdk.strip() or ""
            info = f"{m}  ·  Android {v}"
            if s:
                info += f"  (API {s})"
            root.after(0, lambda: ui["device_info_label"].configure(text=info))
        except Exception:
            pass

    def periodic_check():
        check_device_connection()
        root.after(15000, periodic_check)

    def connect_device():
        from app.ui.dialogs import ProgressOverlay, ResultDialog

        ip = ui["ip_entry"].get().strip()
        port = ui["port_entry"].get().strip()

        if not validate_ip(ip):
            ResultDialog(root, "IP inválida",
                "Ingrese una IP válida.\nEjemplo: 192.168.1.100", "warning")
            return
        if not validate_port(port):
            ResultDialog(root, "Puerto inválido",
                "Ingrese un puerto válido (1-65535).\nEjemplo: 5555", "warning")
            return

        overlay = ProgressOverlay(root, "Conectando...")
        overlay.update_status(f"Iniciando conexión a {ip}:{port}...")
        overlay.start_indeterminate()
        overlay.progress.configure(progress_color=Theme.BLUE)

        def _connect():
            try:
                overlay.update_status("Reiniciando servidor ADB...")
                run_adb(["kill-server"])
                overlay.update_status("Iniciando servidor ADB...")
                run_adb(["start-server"])
                overlay.update_status(f"Conectando a {ip}:{port}...")
                stdout, stderr, _ = run_adb(["connect", f"{ip}:{port}"])

                root.after(0, overlay.close)

                if "connected to" in stdout:
                    config.save(ui["root_path_var"].get(), ip, port)
                    root.after(10, lambda: ResultDialog(root,
                        "Conexión exitosa",
                        f"Conectado por Wi-Fi en {ip}:{port}", "success"))
                    root.after(0, lambda: update_connection_status(True))
                elif "already connected" in stdout:
                    config.save(ui["root_path_var"].get(), ip, port)
                    root.after(10, lambda: ResultDialog(root,
                        "Ya conectado",
                        f"El dispositivo ya está conectado a {ip}:{port}", "info"))
                    root.after(0, lambda: update_connection_status(True))
                else:
                    root.after(10, lambda: ResultDialog(root,
                        "Error de conexión",
                        "No se pudo conectar al dispositivo.",
                        "error", f"{stdout}\n{stderr}"))
                    root.after(0, lambda: update_connection_status(False))
            except Exception as e:
                root.after(0, overlay.close)
                root.after(10, lambda: ResultDialog(root,
                    "Error", str(e), "error"))
        threading.Thread(target=_connect, daemon=True).start()

    # ── Carga de imágenes ────────────────────────────────────────────────

    def _set_image(widget, photo, key):
        ui[key] = photo
        widget.configure(image=photo)

    def _set_tree_icon(kind, photo):
        if kind == "folder":
            ui["folder_icon"] = photo
        else:
            ui["apk_icon"] = photo
        p = ui["root_path_var"].get()
        if p and os.path.isdir(p):
            update_treeview(p)

    def _load_images_async():
        """Carga iconos del treeview desde GitHub en segundo plano."""
        fi = _download_image_safe(
            "https://raw.githubusercontent.com/soypercyabad/images-projects/main/Carpeta.png",
            (18, 18))
        if fi:
            p = ImageTk.PhotoImage(fi)
            root.after(0, lambda: _set_tree_icon("folder", p))

        ai = _download_image_safe(
            "https://raw.githubusercontent.com/soypercyabad/images-projects/main/android.png",
            (18, 18))
        if ai:
            p = ImageTk.PhotoImage(ai)
            root.after(0, lambda: _set_tree_icon("apk", p))

    # ══════════════════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════════════════
    #                      CONSTRUCCIÓN DE LA UI
    # ══════════════════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════════════════

    # ── BANNER ───────────────────────────────────────────────────────────
    banner_path = os.path.join(config.ASSETS_DIR, "assets", "banner.png")
    target_w, target_h = 820, 105
    try:
        banner_img = Image.open(banner_path)
        ratio = max(target_w / banner_img.width, target_h / banner_img.height)
        new_w = int(banner_img.width * ratio)
        new_h = int(banner_img.height * ratio)
        banner_img = banner_img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        banner_img = banner_img.crop((left, top, left + target_w, top + target_h))
    except Exception:
        # Fallback: gradiente si no se encuentra la imagen
        banner_img = Image.new("RGB", (target_w, target_h), "#7C3AED")
        d = ImageDraw.Draw(banner_img)
        for i in range(target_h):
            r = 124 - int(94 * i / target_h)
            g = 58 - int(19 * i / target_h)
            b = 237 - int(210 * i / target_h)
            d.line([(0, i), (target_w, i)], fill=(r, g, b))

    ui["cover_photo"] = ImageTk.PhotoImage(banner_img)
    ui["cover_label"] = ctk.CTkLabel(root, image=ui["cover_photo"], text="")
    ui["cover_label"].pack(fill="x")

    # ── CONTENEDOR PRINCIPAL (DOS COLUMNAS) ──────────────────────────────
    main_container = ctk.CTkFrame(root, fg_color="transparent")
    main_container.pack(fill="x", padx=12, pady=(8, 0))
    main_container.columnconfigure(0, weight=1)
    main_container.columnconfigure(1, weight=1)

    # ── COLUMNA IZQUIERDA ────────────────────────────────────────────────
    left_col = ctk.CTkFrame(main_container, fg_color="transparent")
    left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

    # Card: Estado del dispositivo
    device_card = ctk.CTkFrame(left_col, fg_color=Theme.CARD, corner_radius=12,
                                border_width=1, border_color=Theme.BORDER)
    device_card.pack(fill="x", pady=(0, 6))

    section_header_1 = ctk.CTkFrame(device_card, fg_color="transparent")
    section_header_1.pack(fill="x", padx=14, pady=(10, 4))

    ctk.CTkFrame(section_header_1, fg_color=Theme.PURPLE, width=4, height=16,
                 corner_radius=2).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(section_header_1, text="DISPOSITIVO", font=(Theme.FONT, 14, "bold"),
                 text_color=Theme.TEXT_SEC).pack(side="left")

    from app.ui import help_window
    ctk.CTkButton(
        section_header_1, text="?", command=lambda: help_window.show(root),
        width=26, height=26, corner_radius=13,
        fg_color=Theme.BG, hover_color=Theme.BORDER,
        text_color=Theme.TEXT_SEC, font=(Theme.FONT, 13, "bold"),
    ).pack(side="right")

    status_row = ctk.CTkFrame(device_card, fg_color="transparent")
    status_row.pack(fill="x", padx=14, pady=(2, 4))

    status_left = ctk.CTkFrame(status_row, fg_color="transparent")
    status_left.pack(side="left", fill="y")

    dot_row = ctk.CTkFrame(status_left, fg_color="transparent")
    dot_row.pack(anchor="w")

    ui["status_indicator"] = ctk.CTkFrame(dot_row, fg_color=Theme.RED, width=10, height=10,
                                           corner_radius=5)
    ui["status_indicator"].pack(side="left", padx=(0, 8), pady=4)

    ui["status_label"] = ctk.CTkLabel(dot_row, text="Dispositivo desconectado",
                                       font=(Theme.FONT, 14, "bold"), text_color=Theme.RED)
    ui["status_label"].pack(side="left")

    ui["device_info_label"] = ctk.CTkLabel(status_left, text="Sin dispositivo detectado",
                                            font=(Theme.FONT, 12), text_color=Theme.TEXT_MUTED)
    ui["device_info_label"].pack(anchor="w", pady=(1, 0))

    ctk.CTkButton(
        status_row, text="▶  Trasmitir", command=lambda: run_scrcpy(root),
        width=130, height=36, corner_radius=18,
        fg_color=Theme.PURPLE, hover_color=Theme.PURPLE_HOVER,
        font=(Theme.FONT, 15, "bold"),
    ).pack(side="right")

    ctk.CTkFrame(device_card, fg_color="transparent", height=6).pack()

    # Card: Conexión Wi-Fi
    wifi_card = ctk.CTkFrame(left_col, fg_color=Theme.CARD, corner_radius=12,
                              border_width=1, border_color=Theme.BORDER)
    wifi_card.pack(fill="x", pady=(0, 6))

    section_header_2 = ctk.CTkFrame(wifi_card, fg_color="transparent")
    section_header_2.pack(fill="x", padx=14, pady=(10, 6))

    ctk.CTkFrame(section_header_2, fg_color=Theme.BLUE, width=4, height=16,
                 corner_radius=2).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(section_header_2, text="CONEXIÓN WI-FI", font=(Theme.FONT, 14, "bold"),
                 text_color=Theme.TEXT_SEC).pack(side="left")

    fields_grid = ctk.CTkFrame(wifi_card, fg_color="transparent")
    fields_grid.pack(fill="x", padx=14, pady=(0, 4))
    fields_grid.columnconfigure(0, weight=3)
    fields_grid.columnconfigure(1, weight=1)
    fields_grid.columnconfigure(2, weight=0)

    ctk.CTkLabel(fields_grid, text="IP Address", font=(Theme.FONT, 13, "bold"),
                 text_color=Theme.TEXT_SEC).grid(row=0, column=0, sticky="w", padx=(0, 6))
    ctk.CTkLabel(fields_grid, text="Puerto", font=(Theme.FONT, 13, "bold"),
                 text_color=Theme.TEXT_SEC).grid(row=0, column=1, sticky="w", padx=(0, 6))

    ui["ip_entry"] = ctk.CTkEntry(fields_grid, placeholder_text="192.168.1.100", height=36,
                                    corner_radius=8, border_color=Theme.BORDER,
                                    border_width=2, fg_color=Theme.INPUT_BG,
                                    text_color=Theme.TEXT, font=(Theme.FONT, 15))
    ui["ip_entry"].grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))

    ui["port_entry"] = ctk.CTkEntry(fields_grid, placeholder_text="5555", height=36,
                                      corner_radius=8, border_color=Theme.BORDER,
                                      border_width=2, fg_color=Theme.INPUT_BG,
                                      text_color=Theme.TEXT, font=(Theme.FONT, 15), width=70)
    ui["port_entry"].grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(2, 0))

    ui["connect_btn"] = ctk.CTkButton(
        fields_grid, text="Conectar", command=connect_device,
        width=120, height=36, corner_radius=18,
        fg_color=Theme.BLUE, hover_color=Theme.BLUE_HOVER,
        font=(Theme.FONT, 14, "bold"),
    )
    ui["connect_btn"].grid(row=1, column=2, pady=(2, 0))

    # Cargar config guardada
    default_path, default_ip, default_port = config.load()
    if default_ip:
        ui["ip_entry"].insert(0, default_ip)
    if default_port:
        ui["port_entry"].insert(0, default_port)
    ui["ip_entry"].bind("<FocusOut>", on_field_change)
    ui["port_entry"].bind("<FocusOut>", on_field_change)

    # Nota informativa
    hint_card = ctk.CTkFrame(wifi_card, fg_color="#EFF6FF", corner_radius=8,
                               border_width=1, border_color="#BFDBFE")
    hint_card.pack(fill="x", padx=14, pady=(6, 10))
    ctk.CTkLabel(
        hint_card,
        text="ℹ  Primera vez? Conecte por USB y acepte la autorización de depuración",
        font=(Theme.FONT, 12), text_color="#1E40AF",
        wraplength=400, justify="left",
    ).pack(padx=10, pady=5)

    # ── COLUMNA DERECHA: INSTALAR APK ────────────────────────────────────
    right_col = ctk.CTkFrame(main_container, fg_color="transparent")
    right_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    apk_card = ctk.CTkFrame(right_col, fg_color=Theme.CARD, corner_radius=12,
                              border_width=1, border_color=Theme.BORDER)
    apk_card.pack(fill="x")

    section_header_3 = ctk.CTkFrame(apk_card, fg_color="transparent")
    section_header_3.pack(fill="x", padx=14, pady=(10, 6))

    ctk.CTkFrame(section_header_3, fg_color=Theme.TEAL, width=4, height=16,
                 corner_radius=2).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(section_header_3, text="INSTALAR APK", font=(Theme.FONT, 14, "bold"),
                 text_color=Theme.TEXT_SEC).pack(side="left")

    path_row = ctk.CTkFrame(apk_card, fg_color="transparent")
    path_row.pack(fill="x", padx=14, pady=(0, 4))

    ui["root_path_var"] = tk.StringVar(value=default_path)
    display_path = (default_path if len(default_path) < 25
                    else "..." + default_path[-22:]) if default_path else "Seleccionar carpeta..."

    ui["path_display"] = ctk.CTkLabel(path_row, text=display_path,
                                       font=(Theme.FONT, 12), text_color=Theme.TEXT_SEC,
                                       anchor="w")
    ui["path_display"].pack(side="left", fill="x", expand=True)

    ctk.CTkButton(
        path_row, text="📂", command=select_root_path,
        width=34, height=30, corner_radius=8,
        fg_color=Theme.BG, hover_color=Theme.BORDER,
        text_color=Theme.TEXT, font=(Theme.FONT, 14),
    ).pack(side="left", padx=(4, 4))

    ctk.CTkButton(
        path_row, text="Instalar APK", command=install_apk,
        width=110, height=36, corner_radius=18,
        fg_color=Theme.TEAL, hover_color=Theme.TEAL_HOVER,
        font=(Theme.FONT, 14, "bold"),
    ).pack(side="right")

    # Treeview header
    tree_header = ctk.CTkFrame(apk_card, fg_color="transparent")
    tree_header.pack(fill="x", padx=14, pady=(0, 4))

    ctk.CTkButton(
        tree_header, text="↻",
        command=lambda: update_treeview(ui["root_path_var"].get()),
        width=28, height=24, corner_radius=6,
        fg_color=Theme.BG, hover_color=Theme.BORDER,
        text_color=Theme.TEXT, font=(Theme.FONT, 15, "bold"),
    ).pack(side="left")

    ctk.CTkLabel(tree_header, text="Directorio de APKs", font=(Theme.FONT, 13),
                 text_color=Theme.TEXT_MUTED).pack(side="left", padx=6)

    # Treeview container
    tree_border = ctk.CTkFrame(apk_card, fg_color=Theme.BG, corner_radius=8,
                                 border_width=1, border_color=Theme.BORDER, height=160)
    tree_border.pack(fill="x", padx=14, pady=(0, 12))
    tree_border.pack_propagate(False)

    # Estilos ttk
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Card.Treeview",
        background="white", foreground=Theme.TEXT, fieldbackground="white",
        borderwidth=0, font=(Theme.FONT, 10), rowheight=24)
    style.configure("Card.Treeview.Heading",
        background=Theme.BG, foreground=Theme.TEXT_SEC,
        font=(Theme.FONT, 12, "bold"), borderwidth=0, relief="flat")
    style.map("Card.Treeview",
        background=[("selected", "#EDE9FE")],
        foreground=[("selected", Theme.PURPLE)])
    style.configure("Modern.Vertical.TScrollbar",
        background="#C4C9D0", troughcolor="#F0F2F5", borderwidth=0, width=6,
        arrowsize=0, relief="flat")
    style.map("Modern.Vertical.TScrollbar",
        background=[("active", "#9CA3AF"), ("!active", "#C4C9D0")])
    style.layout("Modern.Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {
            "sticky": "ns",
            "children": [
                ("Vertical.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})
            ]
        })
    ])

    tree_inner = tk.Frame(tree_border, bg="white", padx=4, pady=4)
    tree_inner.pack(fill="x", padx=2, pady=2)

    ui["tree"] = ttk.Treeview(tree_inner, height=10, style="Card.Treeview", show="tree")
    ui["tree"].heading("#0", text="Directorio", anchor="w")

    scrollbar = ttk.Scrollbar(tree_inner, orient="vertical", command=ui["tree"].yview,
                                style="Modern.Vertical.TScrollbar")
    ui["tree"].configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    ui["tree"].pack(fill="both", expand=True, side="left")

    # Iconos placeholder
    ui["folder_icon"] = _create_icon(18, "#FFA726")
    ui["apk_icon"] = _create_icon(18, "#66BB6A")

    # ── FOOTER ───────────────────────────────────────────────────────────
    footer = ctk.CTkFrame(root, fg_color="transparent", height=32)
    footer.pack(fill="x", pady=(2, 4))

    ctk.CTkFrame(footer, fg_color=Theme.BORDER, height=1).pack(fill="x", padx=30, pady=(0, 3))

    credits = ctk.CTkLabel(footer, text="Desarrollado por @soypercyabad",
                             font=(Theme.FONT, 12), text_color=Theme.TEXT_MUTED,
                             cursor="hand2")
    credits.pack()
    credits.bind("<Button-1>", lambda e: _open_github())
    credits.bind("<Enter>", lambda e: credits.configure(text_color=Theme.BLUE))
    credits.bind("<Leave>", lambda e: credits.configure(text_color=Theme.TEXT_MUTED))

    ctk.CTkLabel(footer, text="v2.0", font=(Theme.FONT, 10),
                 text_color=Theme.TEXT_MUTED).pack()

    # ══════════════════════════════════════════════════════════════════════
    # ── INICIO ────────────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════

    atexit.register(close_processes)

    if default_path and os.path.isdir(default_path):
        update_treeview(default_path)

    threading.Thread(target=_load_images_async, daemon=True).start()
    periodic_check()
    root.mainloop()
