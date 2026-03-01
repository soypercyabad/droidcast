# ══════════════════════════════════════════════════════════════════════════════
# app/ui/help_window.py — Ventana de guía de uso
# ══════════════════════════════════════════════════════════════════════════════

import customtkinter as ctk
from app.theme import Theme

SEPARATOR = "────────────────────────────\n"


def show(root):
    """Muestra la guía de uso dentro de la aplicación."""
    win = ctk.CTkToplevel(root)
    win.title("Cómo usar esta aplicación")
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()
    win.configure(fg_color=Theme.CARD)

    ctk.CTkLabel(win, text="Guía Rápida",
                 font=(Theme.FONT, 18, "bold"),
                 text_color=Theme.PURPLE).pack(pady=(16, 4))

    ctk.CTkLabel(win, text="Sigue estos pasos para usar la herramienta",
                 font=(Theme.FONT, 12),
                 text_color=Theme.TEXT_SEC).pack(pady=(0, 10))

    textbox = ctk.CTkTextbox(
        win, width=440, height=320,
        font=(Theme.FONT, 12),
        fg_color=Theme.BG,
        text_color=Theme.TEXT,
        corner_radius=8,
        wrap="word",
    )
    textbox.pack(padx=16, pady=(0, 8))

    guide_text = (
        "CONFIGURACIÓN INICIAL\n"
        + SEPARATOR
        + "1. Activar Opciones de Desarrollador:\n"
        "   Ajustes → Acerca del teléfono → toca\n"
        "   \"Número de compilación\" 7 veces\n\n"
        "2. En Opciones de desarrollador, activa:\n"
        "   • Depuración USB\n"
        "   • Instalar vía USB\n"
        "   • Depuración USB (Ajustes de seguridad)\n"
        "     (solo Xiaomi/Redmi/POCO)\n\n"
        "3. Conecta por cable USB y acepta\n"
        "   la autorización de depuración.\n\n\n"
        "PASO 1: CONECTAR POR WI-FI\n"
        + SEPARATOR
        + "1. En el celular ve a:\n"
        "   Ajustes → Opciones del desarrollador\n"
        "   → Depuración inalámbrica\n"
        "   y copia la IP que aparece\n\n"
        "2. Escribe la IP y puerto (5555)\n"
        "   en los campos de la app\n\n"
        "3. Presiona \"Conectar\" (botón azul)\n\n"
        "4. El punto verde confirma la conexión\n\n\n"
        "PASO 2: TRANSMITIR PANTALLA\n"
        + SEPARATOR
        + "1. Presiona \"▶ Trasmitir\" (botón morado)\n\n"
        "2. Se abrirá una ventana con la pantalla\n"
        "   de tu celular en tiempo real\n\n"
        "3. Puedes interactuar con el mouse\n"
        "   y teclado desde tu PC\n\n\n"
        "PASO 3: INSTALAR APK\n"
        + SEPARATOR
        + "1. Presiona 📂 para elegir la carpeta\n"
        "   donde están tus archivos APK\n\n"
        "2. Selecciona el .apk en el árbol\n\n"
        "3. Presiona \"Instalar APK\" (botón verde)\n\n"
        "4. Si el celular pide permiso, acéptalo\n\n\n"
        "SOLUCIÓN DE PROBLEMAS\n"
        + SEPARATOR
        + "• \"Sin dispositivo\"\n"
        "  → Verifica que la IP sea correcta y\n"
        "    ambos equipos estén en la misma red\n\n"
        "• Sin control táctil al transmitir\n"
        "  → Activa \"Depuración USB (Ajustes de\n"
        "    seguridad)\" y reinicia el celular\n\n"
        "• No se instala el APK\n"
        "  → Activa \"Instalar vía USB\" en\n"
        "    Opciones de desarrollador\n"
    )

    textbox.insert("1.0", guide_text)
    textbox.configure(state="disabled")

    ctk.CTkButton(
        win, text="Entendido", command=win.destroy,
        width=140, height=36, corner_radius=18,
        fg_color=Theme.PURPLE, hover_color=Theme.PURPLE_HOVER,
        font=(Theme.FONT, 14, "bold"),
    ).pack(pady=(4, 16))

    win.update_idletasks()
    w, h = 480, win.winfo_reqheight()
    x = root.winfo_x() + (root.winfo_width() - w) // 2
    y = root.winfo_y() + (root.winfo_height() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
