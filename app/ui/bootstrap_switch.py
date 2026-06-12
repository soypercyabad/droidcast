# ══════════════════════════════════════════════════════════════════════════════
# app/ui/bootstrap_switch.py — Switch al estilo Bootstrap nativo
# ══════════════════════════════════════════════════════════════════════════════

import tkinter as tk
import customtkinter as ctk
from app.theme import Theme

class BootstrapSwitch(ctk.CTkFrame):
    """
    Un interruptor personalizado (switch) con estilo Bootstrap nativo.
    El círculo blanco (thumb) queda completamente contenido dentro del track gris/verde,
    sin sobresalir y con proporciones elegantes.
    """
    def __init__(
        self,
        master,
        width=44,
        height=24,
        fg_color="#CBD5E1",          # Gris sólido para OFF (Bootstrap style)
        progress_color=Theme.GREEN,   # Verde sólido para ON (Theme.GREEN = #16A34A)
        command=None,
        bg_color=Theme.CARD,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", width=width, height=height, **kwargs)
        self.width = width
        self.height = height
        self.track_fg = fg_color
        self.track_progress = progress_color
        self.command = command
        self.bg_color = bg_color
        self._state = False  # False = OFF, True = ON

        # Creamos el Canvas para dibujar las formas exactas
        self.canvas = ctk.CTkCanvas(
            self,
            width=width,
            height=height,
            bg=self.bg_color,
            highlightthickness=0,
            bd=0,
            cursor="hand2"
        )
        self.canvas.pack(fill="both", expand=True)

        # Enlazar evento de click
        self.canvas.bind("<Button-1>", self.toggle)

        # Dibujar estado inicial
        self.draw()

    def toggle(self, event=None):
        self._state = not self._state
        self.draw()
        if self.command:
            self.command()

    def get(self) -> int:
        return 1 if self._state else 0

    def select(self):
        if not self._state:
            self._state = True
            self.draw()

    def deselect(self):
        if self._state:
            self._state = False
            self.draw()

    def draw(self):
        self.canvas.delete("all")

        # Seleccionar color de fondo del track según el estado
        color = self.track_progress if self._state else self.track_fg

        # Dibujar track redondeado (cápsula)
        r = self.height  # El diámetro de los extremos es igual a la altura de la cápsula

        # Extremo izquierdo
        self.canvas.create_oval(
            0, 0, r, r,
            fill=color, outline=color, width=0
        )
        # Extremo derecho
        self.canvas.create_oval(
            self.width - r, 0, self.width, r,
            fill=color, outline=color, width=0
        )
        # Rectángulo conector
        self.canvas.create_rectangle(
            r / 2, 0, self.width - r / 2, r,
            fill=color, outline=color, width=0
        )

        # Dibujar el círculo blanco (thumb)
        # Padding interno de 3.0px para que quede completamente dentro
        padding = 3.0
        thumb_diameter = self.height - (2 * padding)

        if not self._state:
            x0 = padding
        else:
            x0 = self.width - padding - thumb_diameter

        y0 = padding

        self.canvas.create_oval(
            x0, y0, x0 + thumb_diameter, y0 + thumb_diameter,
            fill="#FFFFFF", outline="#FFFFFF", width=0
        )
