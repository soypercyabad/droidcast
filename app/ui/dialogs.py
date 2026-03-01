# ══════════════════════════════════════════════════════════════════════════════
# app/ui/dialogs.py — Diálogos modales reutilizables
# ══════════════════════════════════════════════════════════════════════════════

import customtkinter as ctk
from app.theme import Theme


class ProgressOverlay:
    """Ventana modal de progreso con barra animada y texto de estado."""

    def __init__(self, parent, title="Procesando..."):
        self.win = ctk.CTkToplevel(parent)
        self.win.title(title)
        self.win.geometry("420x155")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(fg_color=Theme.CARD)

        self.win.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 420) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 155) // 2
        self.win.geometry(f"420x155+{x}+{y}")

        self.title_label = ctk.CTkLabel(
            self.win, text=title, font=(Theme.FONT, 15, "bold"),
            text_color=Theme.TEXT)
        self.title_label.pack(pady=(20, 5))

        self.status_label = ctk.CTkLabel(
            self.win, text="Iniciando...", font=(Theme.FONT, 12),
            text_color=Theme.TEXT_SEC)
        self.status_label.pack(pady=(0, 12))

        self.progress = ctk.CTkProgressBar(
            self.win, width=360, height=6, corner_radius=3,
            fg_color=Theme.BORDER, progress_color=Theme.PURPLE)
        self.progress.pack(pady=(0, 5))
        self.progress.set(0)

        self.pct_label = ctk.CTkLabel(
            self.win, text="", font=(Theme.FONT, 10),
            text_color=Theme.TEXT_MUTED)
        self.pct_label.pack()

        self._indeterminate = False
        self._ind_value = 0.0
        self._ind_direction = 1

    def update_status(self, text):
        self.win.after(0, lambda: self.status_label.configure(text=text))

    def update_progress(self, value):
        """value entre 0.0 y 1.0"""
        self.win.after(0, lambda: self.progress.set(value))
        pct = int(value * 100)
        self.win.after(0, lambda: self.pct_label.configure(text=f"{pct}%"))

    def start_indeterminate(self):
        self._indeterminate = True
        self._ind_value = 0.0
        self._animate_indeterminate()

    def _animate_indeterminate(self):
        if not self._indeterminate:
            return
        remaining = 0.92 - self._ind_value
        speed = max(remaining * 0.015, 0.001)
        self._ind_value = min(self._ind_value + speed, 0.92)
        self.progress.set(self._ind_value)
        self.pct_label.configure(text="")
        self.win.after(80, self._animate_indeterminate)

    def finish_progress(self):
        """Llena la barra a 100% suavemente al completar."""
        self._indeterminate = False
        self.progress.set(1.0)
        self.pct_label.configure(text="")

    def close(self):
        self._indeterminate = False
        try:
            self.win.grab_release()
            self.win.destroy()
        except Exception:
            pass


class ResultDialog:
    """Diálogo de resultado personalizado con diseño moderno."""

    def __init__(self, parent, title, message, dialog_type="success", detail=None, wait=False):
        self.win = ctk.CTkToplevel(parent)
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(fg_color=Theme.CARD)

        types = {
            "success": ("#10B981", "✓", "#ECFDF5"),
            "warning": ("#F59E0B", "⚠", "#FFFBEB"),
            "error":   ("#EF4444", "✕", "#FEF2F2"),
            "info":    (Theme.BLUE, "ℹ", "#EFF6FF"),
        }
        color, icon, bg = types.get(dialog_type, types["info"])

        icon_frame = ctk.CTkFrame(self.win, fg_color=bg, width=50, height=50,
                                   corner_radius=25)
        icon_frame.pack(pady=(20, 8))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text=icon, font=(Theme.FONT, 22, "bold"),
                     text_color=color).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self.win, text=title, font=(Theme.FONT, 15, "bold"),
                     text_color=Theme.TEXT).pack(pady=(0, 4))

        ctk.CTkLabel(self.win, text=message, font=(Theme.FONT, 12),
                     text_color=Theme.TEXT_SEC, wraplength=340,
                     justify="center").pack(padx=20, pady=(0, 4))

        if detail:
            detail_frame = ctk.CTkFrame(self.win, fg_color=Theme.BG,
                                         corner_radius=8)
            detail_frame.pack(fill="x", padx=20, pady=(4, 4))
            ctk.CTkLabel(detail_frame, text=detail, font=(Theme.FONT, 11),
                         text_color=Theme.TEXT_MUTED, wraplength=320,
                         justify="left").pack(padx=10, pady=8)

        ctk.CTkButton(
            self.win, text="Aceptar", command=self._close,
            width=120, height=34, corner_radius=17,
            fg_color=color, hover_color=color,
            font=(Theme.FONT, 13, "bold"),
        ).pack(pady=(8, 16))

        self.win.update_idletasks()
        w = 400
        h = self.win.winfo_reqheight()
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")

        if wait:
            self.win.wait_window()

    def _close(self):
        try:
            self.win.grab_release()
            self.win.destroy()
        except Exception:
            pass


class ConfirmDialog:
    """Diálogo de confirmación (Confirmar / Cancelar)."""

    def __init__(self, parent, title, message):
        self.result = False
        self.win = ctk.CTkToplevel(parent)
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(fg_color=Theme.CARD)

        icon_frame = ctk.CTkFrame(self.win, fg_color="#EFF6FF", width=50, height=50,
                                   corner_radius=25)
        icon_frame.pack(pady=(20, 8))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text="?", font=(Theme.FONT, 22, "bold"),
                     text_color=Theme.BLUE).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self.win, text=title, font=(Theme.FONT, 15, "bold"),
                     text_color=Theme.TEXT).pack(pady=(0, 4))

        ctk.CTkLabel(self.win, text=message, font=(Theme.FONT, 12),
                     text_color=Theme.TEXT_SEC, wraplength=340,
                     justify="center").pack(padx=20, pady=(0, 16))

        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))

        ctk.CTkButton(
            btn_frame, text="Cancelar", command=self._cancel,
            width=100, height=34, corner_radius=17,
            fg_color=Theme.BORDER, hover_color="#CBD5E1",
            text_color=Theme.TEXT, font=(Theme.FONT, 13),
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="Confirmar", command=self._confirm,
            width=100, height=34, corner_radius=17,
            fg_color=Theme.BLUE, hover_color="#2563EB",
            font=(Theme.FONT, 13, "bold"),
        ).pack(side="left", padx=10)

        self.win.update_idletasks()
        w = 400
        h = self.win.winfo_reqheight()
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.wait_window()

    def _confirm(self):
        self.result = True
        self.win.destroy()

    def _cancel(self):
        self.result = False
        self.win.destroy()
