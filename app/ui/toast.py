import tkinter as tk
import customtkinter as ctk
from app.theme import Theme

class ToastManager:
    _active_toasts = []
    
    @classmethod
    def show(cls, root, title: str, message: str, type: str = "success"):
        toast = ToastNotification(root, title, message, type)
        cls._active_toasts.append(toast)
        cls._rearrange()
        
    @classmethod
    def remove(cls, toast):
        if toast in cls._active_toasts:
            cls._active_toasts.remove(toast)
            cls._rearrange()
            
    @classmethod
    def _rearrange(cls):
        # Mueve cada toast a su nueva posición apilada
        for i, toast in enumerate(reversed(cls._active_toasts)):
            h = toast.height if hasattr(toast, 'height') and toast.height > 10 else 90
            # 60px de margen desde el borde inferior de la pantalla + el alto del propio toast
            y = toast_screen_h - h - 60 - (i * (h + 10))
            toast.move_to_y(y)

# Variable global para altura (se asigna al crear el primer toast)
toast_screen_h = 1080 

class ToastNotification:
    def __init__(self, root, title: str, message: str, type: str = "success"):
        global toast_screen_h
        toast_screen_h = root.winfo_screenheight()
        
        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.0)
        
        # Color clave para que los bordes redondeados del frame se vean bien en Windows
        _KEY = "#010101"
        self.win.configure(bg=_KEY)
        self.win.wm_attributes("-transparentcolor", _KEY)
        
        # Colores según tipo (guiado por figma)
        if type == "error":
            icon_bg = "#FFF1F2"  # Rojo muy pálido
            icon_fg = "#F43F5E"  # Rojo para la X
            icon_char = "✕"
            bar_color = "#F43F5E"
        else:
            icon_bg = "#ECFDF5"
            icon_fg = "#10B981"
            icon_char = "✓"
            bar_color = "#10B981"
            
        # Contenedor principal: Blanco puro, borde negro fino
        self.frame = ctk.CTkFrame(self.win, fg_color="#FFFFFF", corner_radius=12, border_width=1, border_color="#1F2937")
        self.frame.pack(padx=2, pady=2, fill="both", expand=True)
        
        self.frame.columnconfigure(1, weight=1)
        
        # Icono circular
        icon_lbl = ctk.CTkLabel(
            self.frame, text=icon_char, font=(Theme.FONT, 18), 
            text_color=icon_fg, fg_color=icon_bg, width=36, height=36, corner_radius=18
        )
        icon_lbl.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=(16, 8), sticky="nw")
        
        # Título
        title_lbl = ctk.CTkLabel(self.frame, text=title, font=(Theme.FONT, 15, "bold"), text_color="#111827")
        title_lbl.grid(row=0, column=1, sticky="w", pady=(16, 0))
        
        # Botón Cerrar (X muy delgada)
        close_btn = ctk.CTkButton(
            self.frame, text="x", font=(Theme.FONT, 15, "bold"), text_color="#6B7280",
            fg_color="transparent", hover_color="#F3F4F6", width=24, height=24, corner_radius=4,
            command=self.close
        )
        close_btn.grid(row=0, column=2, padx=(8, 16), pady=(12, 0), sticky="ne")
        
        # Mensaje
        msg_lbl = ctk.CTkLabel(self.frame, text=message, font=(Theme.FONT, 13), text_color="#374151", justify="left")
        msg_lbl.grid(row=1, column=1, columnspan=2, sticky="w", pady=(4, 16))
        
        # Barra de progreso inferior (más delgada como el figma)
        self.progress_frame = ctk.CTkFrame(self.frame, fg_color="transparent", height=2, corner_radius=0)
        self.progress_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        
        self.progress_bar = ctk.CTkFrame(self.progress_frame, fg_color=bar_color, height=2, corner_radius=0, width=300)
        self.progress_bar.place(relx=0, rely=0, anchor="nw")
        
        self.win.update_idletasks()
        
        self.width = max(320, self.win.winfo_reqwidth())
        self.height = max(90, self.win.winfo_reqheight()) # Forzar mínimo para evitar fallos de Tkinter
        
        # Geometría inicial (el Y final lo asigna el ToastManager de inmediato)
        self.screen_w = root.winfo_screenwidth()
        self.current_x = self.screen_w
        self.target_y = toast_screen_h - self.height - 60
        
        self.win.geometry(f"{self.width}x{self.height}+{self.current_x}+{self.target_y}")
        self.win.deiconify()
        
        self.alpha = 0.0
        self.time_left = 3000 # 3 segundos
        self._animate_in()
        self._update_progress()
        
    def move_to_y(self, y):
        self.target_y = y
        self._animate_move()
        
    def _animate_move(self):
        if not self.win.winfo_exists(): return
        current_y = self.win.winfo_y()
        if abs(current_y - self.target_y) > 1:
            step = (self.target_y - current_y) // 4
            if step == 0: step = 1 if self.target_y > current_y else -1
            self.win.geometry(f"+{self.current_x}+{current_y + step}")
            self.win.after(16, self._animate_move)
        else:
            self.win.geometry(f"+{self.current_x}+{self.target_y}")

    def _animate_in(self):
        if not self.win.winfo_exists(): return
        target_x = self.screen_w - self.width - 24
        if self.current_x > target_x:
            self.current_x -= max(2, (self.current_x - target_x) // 4)
            self.alpha = min(1.0, self.alpha + 0.1)
            self.win.geometry(f"+{self.current_x}+{self.win.winfo_y()}")
            self.win.attributes("-alpha", self.alpha)
            self.win.after(16, self._animate_in)
            
    def _update_progress(self):
        if not self.win.winfo_exists(): return
        self.time_left -= 16
        if self.time_left <= 0:
            self.close()
        else:
            # Actualizar ancho de la barra (300px es el max estimado)
            ratio = max(0, self.time_left / 3000.0)
            self.progress_bar.configure(width=max(1, int(self.width * ratio)))
            self.win.after(16, self._update_progress)
            
    def close(self):
        self._animate_out()
        
    def _animate_out(self):
        if not self.win.winfo_exists(): return
        if self.current_x < self.screen_w:
            self.current_x += max(2, (self.screen_w - self.current_x) // 4)
            self.alpha = max(0.0, self.alpha - 0.1)
            self.win.geometry(f"+{self.current_x}+{self.win.winfo_y()}")
            self.win.attributes("-alpha", self.alpha)
            self.win.after(16, self._animate_out)
        else:
            ToastManager.remove(self)
            self.win.destroy()
