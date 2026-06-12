# ══════════════════════════════════════════════════════════════════════════════
# app/ui/json_formatter.py — Ventana de herramienta Formateador JSON
# ══════════════════════════════════════════════════════════════════════════════

import json
import customtkinter as ctk
from app.theme import Theme

def show(root):
    """Muestra la ventana del Formateador JSON."""
    win = ctk.CTkToplevel(root)
    win.title("Formateador JSON - DroidCast")
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()
    win.configure(fg_color=Theme.CARD)

    # Header
    ctk.CTkLabel(
        win, text="{ } Formateador JSON",
        font=(Theme.FONT, 18, "bold"),
        text_color=Theme.PURPLE
    ).pack(pady=(16, 4))

    ctk.CTkLabel(
        win, text="Pega tu JSON desordenado o minificado aquí abajo y formatéalo al instante.",
        font=(Theme.FONT, 12),
        text_color=Theme.TEXT_SEC
    ).pack(pady=(0, 12))

    # Textbox principal
    textbox = ctk.CTkTextbox(
        win, width=560, height=300,
        font=("Consolas", 11),  # Monoespaciado para código
        fg_color=Theme.BG,
        text_color=Theme.TEXT,
        corner_radius=8,
        wrap="none",  # Permitir scroll horizontal si es necesario
    )
    textbox.pack(padx=16, pady=(0, 8))

    # Etiqueta de estado
    status_label = ctk.CTkLabel(
        win, text="Listo para procesar JSON",
        font=(Theme.FONT, 11, "bold"),
        text_color=Theme.TEXT_MUTED
    ).pack(pady=(2, 8))

    def get_status_label():
        # Retorna el widget de estado para poder cambiar su texto y color
        # Dado que pack() devuelve None, buscaremos entre los hijos del frame
        for child in win.winfo_children():
            if isinstance(child, ctk.CTkLabel) and child.cget("font") == (Theme.FONT, 11, "bold"):
                return child
        return None

    def format_json():
        lbl = get_status_label()
        raw_text = textbox.get("1.0", "end-1c").strip()
        if not raw_text:
            if lbl:
                lbl.configure(text="¡Cuidado! El cuadro está vacío", text_color=Theme.ORANGE)
            return
        
        try:
            parsed = json.loads(raw_text)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            textbox.delete("1.0", "end")
            textbox.insert("1.0", formatted)
            if lbl:
                lbl.configure(text="✔ ¡JSON formateado con éxito!", text_color=Theme.GREEN)
        except json.JSONDecodeError as e:
            if lbl:
                lbl.configure(text=f"❌ Error en JSON: {str(e)}", text_color=Theme.RED)

    def minify_json():
        lbl = get_status_label()
        raw_text = textbox.get("1.0", "end-1c").strip()
        if not raw_text:
            if lbl:
                lbl.configure(text="¡Cuidado! El cuadro está vacío", text_color=Theme.ORANGE)
            return
        
        try:
            parsed = json.loads(raw_text)
            minified = json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
            textbox.delete("1.0", "end")
            textbox.insert("1.0", minified)
            if lbl:
                lbl.configure(text="✔ ¡JSON minificado con éxito!", text_color=Theme.GREEN)
        except json.JSONDecodeError as e:
            if lbl:
                lbl.configure(text=f"❌ Error en JSON: {str(e)}", text_color=Theme.RED)

    def copy_json():
        lbl = get_status_label()
        text = textbox.get("1.0", "end-1c").strip()
        if not text:
            if lbl:
                lbl.configure(text="¡Cuidado! Nada que copiar", text_color=Theme.ORANGE)
            return
        
        win.clipboard_clear()
        win.clipboard_append(text)
        if lbl:
            lbl.configure(text="✔ ¡Copiado al portapapeles!", text_color=Theme.GREEN)

    def clear_all():
        lbl = get_status_label()
        textbox.delete("1.0", "end")
        if lbl:
            lbl.configure(text="Cuadro limpiado. Listo.", text_color=Theme.TEXT_MUTED)

    # Panel de botones
    btn_frame = ctk.CTkFrame(win, fg_color="transparent")
    btn_frame.pack(fill="x", padx=16, pady=(4, 16))

    ctk.CTkButton(
        btn_frame, text="✨ Formatear", command=format_json,
        width=120, height=36, corner_radius=18,
        fg_color=Theme.PURPLE, hover_color=Theme.PURPLE_HOVER,
        font=(Theme.FONT, 13, "bold"),
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        btn_frame, text="🗜 Minificar", command=minify_json,
        width=110, height=36, corner_radius=18,
        fg_color="#475569", hover_color="#334155",
        font=(Theme.FONT, 13, "bold"), text_color=Theme.WHITE
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        btn_frame, text="📋 Copiar", command=copy_json,
        width=110, height=36, corner_radius=18,
        fg_color=Theme.TEAL, hover_color=Theme.TEAL_HOVER,
        font=(Theme.FONT, 13, "bold"), text_color=Theme.WHITE
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        btn_frame, text="🗑 Limpiar", command=clear_all,
        width=110, height=36, corner_radius=18,
        fg_color=Theme.RED, hover_color=Theme.RED_HOVER,
        font=(Theme.FONT, 13, "bold"), text_color=Theme.WHITE
    ).pack(side="right")

    win.update_idletasks()
    w, h = 600, win.winfo_reqheight()
    x = root.winfo_x() + (root.winfo_width() - w) // 2
    y = root.winfo_y() + (root.winfo_height() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
