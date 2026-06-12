# ══════════════════════════════════════════════════════════════════════════════
# app/ui/log_viewer.py — Copia fiel de LambdaTest Network Logs en DroidCast
# ══════════════════════════════════════════════════════════════════════════════

import subprocess
import threading
import os
import re
import json
import customtkinter as ctk
from app.theme import Theme
from app.core.adb import get_adb_path
from app.core import device as _device

class LogViewerWindow:
    def __init__(self, root):
        self.root = root
        self.win = ctk.CTkToplevel(root)
        self.win.title("Network Logs - LambdaTest Copy")
        self.win.geometry("960x600")
        self.win.minsize(920, 520)
        self.win.transient(root)
        
        # Paleta de colores oscura exacta de LambdaTest
        self.BG_DARK = "#0F0F12"
        self.CARD_DARK = "#16161A"
        self.BORDER_DARK = "#26262B"
        self.TEXT_WHITE = "#FFFFFF"
        self.TEXT_GRAY = "#A0A0A5"
        self.PILL_BG = "#222227"
        self.PILL_SELECTED = "#3E3E47"
        self.INPUT_BG = "#1A1A1F"

        self.win.configure(fg_color=self.BG_DARK)

        # Variables de estado
        self.requests = []          # Lista de peticiones
        self.active_requests = {}   # TID -> Request dict
        self.process = None
        self.running = False
        self.paused = False
        self.selected_req = None    # Request seleccionado
        self.current_tab = "Headers" # Headers o Response
        self.active_filter = "All"  # All, JS, CSS, Img, Media, Font, Doc, WS

        self.row_widgets = {}       # req_id -> dict de widgets de la fila

        self.build_ui()
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

        # Autostart logs
        if _device.check_connection():
            self.start_capture()
        else:
            self.append_log_direct("⚠ Dispositivo desconectado. Conecte y encienda captura.", "warning")

    def build_ui(self):
        # ─── 1. TOP SECTION (Network Logs Header + Pills + Search) ───
        top_frame = ctk.CTkFrame(self.win, fg_color=self.BG_DARK, corner_radius=0)
        top_frame.pack(fill="x", side="top", padx=16, pady=(12, 4))

        # Fila 1: Título "Network Logs" + Status + Botón Iniciar/Detener
        header_row = ctk.CTkFrame(top_frame, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 10))

        title_lbl = ctk.CTkLabel(
            header_row, text="Network Logs",
            font=(Theme.FONT, 20, "bold"),
            text_color=self.TEXT_WHITE
        )
        title_lbl.pack(side="left")

        # Botón Iniciar / Detener
        self.btn_toggle = ctk.CTkButton(
            header_row, text="Iniciar", width=90, height=28, corner_radius=4,
            fg_color=Theme.GREEN, hover_color="#15803D", text_color=self.TEXT_WHITE,
            font=(Theme.FONT, 13, "bold"),
            command=self.toggle_capture
        )
        self.btn_toggle.pack(side="right", padx=(8, 0))

        # Status Label
        self.status_lbl = ctk.CTkLabel(
            header_row, text="Detenido",
            font=(Theme.FONT, 13, "bold"),
            text_color=Theme.RED
        )
        self.status_lbl.pack(side="right")

        # Fila 2: Píldoras de filtros estilo LambdaTest (All, JS, CSS, Img, Media, Font, Doc, WS)
        pills_row = ctk.CTkFrame(top_frame, fg_color="transparent")
        pills_row.pack(fill="x", pady=(0, 8))

        self.pill_buttons = {}
        pills = ["All", "JS", "CSS", "Img", "Media", "Font", "Doc", "WS"]
        for p in pills:
            btn = ctk.CTkButton(
                pills_row, text=p, width=54, height=28, corner_radius=4,
                fg_color=self.PILL_SELECTED if p == "All" else self.PILL_BG,
                hover_color="#2D2D35",
                text_color=self.TEXT_WHITE if p == "All" else self.TEXT_GRAY,
                font=(Theme.FONT, 13, "bold"),
                command=lambda pill=p: self.select_filter_pill(pill)
            )
            btn.pack(side="left", padx=3)
            self.pill_buttons[p] = btn

        # Fila 3: Controles de búsqueda y filtros
        controls_row = ctk.CTkFrame(top_frame, fg_color="transparent")
        controls_row.pack(fill="x", pady=4)

        # Dropdown simulado URL
        dropdown_btn = ctk.CTkButton(
            controls_row, text="URL ▾", width=70, height=28, corner_radius=4,
            fg_color=self.PILL_BG, hover_color="#2D2D35", text_color=self.TEXT_WHITE,
            font=(Theme.FONT, 13, "bold")
        )
        dropdown_btn.pack(side="left", padx=(0, 6))

        # Campo de búsqueda
        self.search_entry = ctk.CTkEntry(
            controls_row, placeholder_text="Search",
            width=320, height=28, corner_radius=4,
            border_color=self.BORDER_DARK, border_width=1,
            fg_color=self.INPUT_BG, text_color=self.TEXT_WHITE,
            font=(Theme.FONT, 13)
        )
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda e: self.apply_filters())

        # Toggles a la derecha (Errors Only / Show Connect)
        self.errors_only_var = ctk.BooleanVar(value=False)
        self.errors_only_chk = ctk.CTkCheckBox(
            controls_row, text="Errors Only", variable=self.errors_only_var,
            font=(Theme.FONT, 13, "bold"), text_color=self.TEXT_GRAY,
            fg_color=Theme.PURPLE, hover_color=Theme.PURPLE_HOVER,
            width=110, height=28, command=self.apply_filters
        )
        self.errors_only_chk.pack(side="left", padx=16)

        self.show_connect_var = ctk.BooleanVar(value=True)
        self.show_connect_chk = ctk.CTkCheckBox(
            controls_row, text="Show Connect", variable=self.show_connect_var,
            font=(Theme.FONT, 13, "bold"), text_color=self.TEXT_GRAY,
            fg_color=Theme.PURPLE, hover_color=Theme.PURPLE_HOVER,
            width=120, height=28, command=self.apply_filters
        )
        self.show_connect_chk.pack(side="left")

        # ─── 2. CONTENEDOR SPLIT (Lista izquierda / Detalle derecho) ───
        self.split_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        self.split_frame.pack(fill="both", expand=True, padx=16, pady=(4, 0))

        # Contenedor Izquierdo (Lista de peticiones con borde arriba y abajo)
        self.left_pane = ctk.CTkFrame(self.split_frame, fg_color=self.BG_DARK, corner_radius=0)
        self.left_pane.pack(fill="both", expand=True, side="left")

        # Cabecera de columnas (Solo visible cuando NO hay elemento seleccionado)
        self.table_header = ctk.CTkFrame(self.left_pane, fg_color=self.BG_DARK, height=26, corner_radius=0)
        self.table_header.pack(fill="x", side="top", pady=(0, 2))
        self.build_table_headers()

        # Separador horizontal sutil
        self.sep_line = ctk.CTkFrame(self.left_pane, fg_color=self.BORDER_DARK, height=1)
        self.sep_line.pack(fill="x", side="top")

        # Lista Scrollable principal
        self.list_scroll = ctk.CTkScrollableFrame(self.left_pane, fg_color=self.BG_DARK, label_text="", corner_radius=0)
        self.list_scroll.pack(fill="both", expand=True)

        # Contenedor Derecho (Detalles) - Oculto al inicio
        self.right_pane = ctk.CTkFrame(self.split_frame, fg_color=self.BG_DARK, corner_radius=0, width=540)

        # ─── 3. BOTTOM CONTROL BAR (Clear logs, Pause, Download) ───
        bottom_bar = ctk.CTkFrame(self.win, fg_color=self.BG_DARK, height=44)
        bottom_bar.pack(fill="x", side="bottom", padx=16, pady=8)

        # Botón Clear logs
        ctk.CTkButton(
            bottom_bar, text="Limpiar Logs", command=self.clear_logs,
            width=110, height=28, corner_radius=4,
            fg_color="transparent", hover_color="#222227", text_color=self.TEXT_WHITE,
            border_width=1, border_color=self.BORDER_DARK,
            font=(Theme.FONT, 13, "bold")
        ).pack(side="left")

        # Check Auto-Scroll
        self.auto_scroll_var = ctk.BooleanVar(value=True)
        self.auto_scroll_chk = ctk.CTkCheckBox(
            bottom_bar, text="Auto-Scroll", variable=self.auto_scroll_var,
            font=(Theme.FONT, 13, "bold"), text_color=self.TEXT_GRAY,
            fg_color=Theme.PURPLE, hover_color=Theme.PURPLE_HOVER
        )
        self.auto_scroll_chk.pack(side="left", padx=16)

        # Botón Descargar / Guardar
        self.btn_download = ctk.CTkButton(
            bottom_bar, text="Exportar JSON", command=self.download_logs,
            width=120, height=28, corner_radius=4,
            fg_color=self.PILL_BG, hover_color="#2D2D35", text_color=self.TEXT_WHITE,
            font=(Theme.FONT, 13, "bold")
        )
        self.btn_download.pack(side="right", padx=(6, 0))

        # Botón Pause / Play
        self.btn_bottom_pause = ctk.CTkButton(
            bottom_bar, text="Pausar", command=self.toggle_pause,
            width=90, height=28, corner_radius=4,
            fg_color=self.PILL_BG, hover_color="#2D2D35", text_color=self.TEXT_WHITE,
            font=(Theme.FONT, 13, "bold")
        )
        self.btn_bottom_pause.pack(side="right")

    def build_table_headers(self):
        # Limpiar headers anteriores
        for c in self.table_header.winfo_children():
            c.destroy()

        # Spacer frame to account for scrollbar in list_scroll
        spacer = ctk.CTkFrame(self.table_header, width=16, height=1, fg_color="transparent")
        spacer.pack(side="right")

        columns = [
            ("URL / Name", 220),
            ("Status", 65),
            ("Method", 75),
            ("Domain", 130),
            ("Type", 60),
            ("Size", 70),
            ("Time", 90)
        ]

        for text, width in columns:
            if text == "URL / Name":
                lbl = ctk.CTkLabel(
                    self.table_header, text=text, font=(Theme.FONT, 13, "bold"),
                    text_color=self.TEXT_GRAY, anchor="w"
                )
                lbl.pack(side="left", fill="x", expand=True, padx=(10, 4))
            else:
                lbl = ctk.CTkLabel(
                    self.table_header, text=text, font=(Theme.FONT, 13, "bold"),
                    text_color=self.TEXT_GRAY, anchor="w", width=width
                )
                lbl.pack(side="left", padx=4)

    def select_filter_pill(self, active_pill):
        self.active_filter = active_pill
        for pill, btn in self.pill_buttons.items():
            if pill == active_pill:
                btn.configure(fg_color=self.PILL_SELECTED, text_color=self.TEXT_WHITE)
            else:
                btn.configure(fg_color=self.PILL_BG, text_color=self.TEXT_GRAY)
        self.apply_filters()

    def toggle_capture(self):
        if self.running:
            self.stop_capture()
        else:
            self.start_capture()

    def toggle_pause(self):
        if self.paused:
            self.paused = False
            self.btn_bottom_pause.configure(text="Pausar", fg_color=self.PILL_BG)
            self.append_log_direct("▶ Reanudado.", "success")
        else:
            self.paused = True
            self.btn_bottom_pause.configure(text="Reanudar", fg_color=Theme.ORANGE)
            self.append_log_direct("⏸ Pausado.", "warning")

    def start_capture(self):
        if self.running:
            return
        self.running = True
        self.paused = False
        self.btn_toggle.configure(text="Detener", fg_color=Theme.RED, hover_color=Theme.RED_HOVER)
        self.status_lbl.configure(text="● Capturando", text_color=Theme.GREEN)

        try:
            subprocess.run([get_adb_path(), "logcat", "-c"], creationflags=subprocess.CREATE_NO_WINDOW, timeout=2)
        except Exception:
            pass

        self.append_log_direct("📡 Analizando logs de red del dispositivo...", "success")
        threading.Thread(target=self._stream_logcat, daemon=True).start()

    def stop_capture(self):
        if not self.running:
            return
        self.running = False
        self.btn_toggle.configure(text="Iniciar", fg_color=Theme.GREEN, hover_color="#15803D")
        self.status_lbl.configure(text="Detenido", text_color=Theme.RED)

        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass
            self.process = None
        self.append_log_direct("⏹ Analizador detenido.", "error")

    def _stream_logcat(self):
        adb = get_adb_path()
        cmd = [adb, "logcat", "-v", "threadtime"]
        logcat_re = re.compile(r'^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+(.*?):\s+(.*)$')

        try:
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            while self.running and self.process:
                line = self.process.stdout.readline()
                if not line:
                    break

                if self.paused:
                    continue

                m = logcat_re.match(line)
                if not m:
                    continue

                tid = m.group(2)
                tag = m.group(4).strip()
                msg = m.group(5).strip()

                self.parse_okhttp_log(tid, tag, msg)

        except Exception as e:
            self.root.after(0, lambda err=str(e): self.append_log_direct(f"❌ Error ADB: {err}"))
        finally:
            self.running = False

    def parse_okhttp_log(self, tid, tag, msg):
        # 1. Nueva petición detectada
        if "--> GET " in msg or "--> POST " in msg or "--> PUT " in msg or "--> DELETE " in msg:
            match = re.search(r'--> (GET|POST|PUT|DELETE)\s+(https?://\S+)', msg)
            if match:
                method = match.group(1)
                url = match.group(2)
                
                domain_match = re.search(r'https?://([^/]+)', url)
                domain = domain_match.group(1) if domain_match else "unknown"
                
                # Nombre de la petición (exactamente como en LambdaTest)
                parsed_path = url.split('/')[-1]
                name = parsed_path if parsed_path else url
                if len(name) > 36:
                    name = name[:33] + "..."

                # Adivinar tipo por extensión de URL y patrones CDN
                url_lower = url.lower()
                guessed_type = 'json'
                if '.js' in url_lower or 'javascript' in url_lower:
                    guessed_type = 'js'
                elif '.css' in url_lower:
                    guessed_type = 'css'
                elif any(ext in url_lower for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.bmp']) or any(kw in url_lower for kw in ['/images/', '/img/', '/avatar/', '/photo/', '/cdn/', 'image=', 'img=']):
                    guessed_type = 'image'
                elif any(ext in url_lower for ext in ['.mp4', '.mp3', '.ogg', '.webm']):
                    guessed_type = 'media'
                elif any(ext in url_lower for ext in ['.woff', '.woff2', '.ttf', '.otf', '.eot']):
                    guessed_type = 'font'
                elif any(ext in url_lower for ext in ['.doc', '.docx', '.pdf', '.xls', '.xlsx']):
                    guessed_type = 'doc'
                elif 'ws://' in url_lower or 'wss://' in url_lower:
                    guessed_type = 'ws'
                elif 'json' not in url_lower:
                    guessed_type = 'other'

                req_id = len(self.requests)
                req = {
                    'id': req_id,
                    'method': method,
                    'url': url,
                    'name': name,
                    'domain': domain,
                    'status': '...',
                    'time': '...',
                    'size': '...',
                    'type': guessed_type,
                    'req_headers': [],
                    'resp_headers': [],
                    'req_body': '',
                    'resp_body': '',
                    'state': 'req_headers'
                }
                
                self.requests.append(req)
                self.active_requests[tid] = req
                self.root.after(0, lambda r=req: self.add_request_row(r))

        # 2. Si ya hay una petición activa en este hilo
        elif tid in self.active_requests:
            req = self.active_requests[tid]

            # Respuesta recibida
            if msg.startswith("<-- ") and not msg.startswith("<-- END"):
                # Intentamos extraer status y tiempo (ej: <-- 200 OK (123ms) o <-- 200 OK https://... (123ms))
                status_match = re.search(r'<-- (\d{3})(?:\s+[^\(]+)?\s*\((\d+ms)\)', msg)
                if status_match:
                    req['status'] = status_match.group(1)
                    ms_val = int(status_match.group(2).replace('ms', ''))
                    req['time'] = f"{ms_val/1000:.2f} s" if ms_val >= 1000 else f"{ms_val} ms"
                    req['state'] = 'resp_headers'
                    self.root.after(0, lambda r=req: self.update_request_row(r))
                else:
                    status_match_simple = re.search(r'<-- (\d{3})', msg)
                    if status_match_simple:
                        req['status'] = status_match_simple.group(1)
                        req['state'] = 'resp_headers'
                        self.root.after(0, lambda r=req: self.update_request_row(r))
                return

            # Cabeceras de petición
            if req['state'] == 'req_headers':
                if msg == "" or "{" in msg or "[" in msg:
                    req['state'] = 'req_body'
                    if "{" in msg or "[" in msg:
                        req['req_body'] += msg
                elif msg.startswith("--> END "):
                    req['state'] = 'requesting'
                    try:
                        parsed = json.loads(req['req_body'])
                        req['req_body'] = json.dumps(parsed, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                elif ":" in msg:
                    req['req_headers'].append(msg)

            # Cuerpo de petición
            elif req['state'] == 'req_body':
                if msg.startswith("--> END "):
                    req['state'] = 'requesting'
                    try:
                        parsed = json.loads(req['req_body'])
                        req['req_body'] = json.dumps(parsed, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                else:
                    req['req_body'] += msg

            # Recolectar cabeceras de respuesta
            elif req['state'] == 'resp_headers':
                if msg == "" or "{" in msg or "[" in msg: 
                    req['state'] = 'resp_body'
                    if "{" in msg or "[" in msg:
                        req['resp_body'] += msg
                elif ":" in msg:
                    req['resp_headers'].append(msg)
                    msg_lower = msg.lower()
                    if "content-length:" in msg_lower:
                        try:
                            bytes_size = int(msg.split(":")[-1].strip())
                            if bytes_size >= 1024:
                                req['size'] = f"{bytes_size / 1024:.1f} KB"
                            else:
                                req['size'] = f"{bytes_size} B"
                            self.root.after(0, lambda r=req: self.update_request_row(r))
                        except Exception:
                            pass
                    if "content-type:" in msg_lower:
                        if "json" in msg_lower: req['type'] = "json"
                        elif "image" in msg_lower or "jpeg" in msg_lower or "png" in msg_lower: req['type'] = "image"
                        elif "javascript" in msg_lower or "js" in msg_lower: req['type'] = "js"
                        elif "css" in msg_lower: req['type'] = "css"
                        else: req['type'] = "other"
                        self.root.after(0, lambda r=req: self.update_request_row(r))

            # Recolectar cuerpo de respuesta
            elif req['state'] == 'resp_body':
                if msg.startswith("<-- END HTTP"):
                    req['state'] = 'done'
                    if tid in self.active_requests:
                        del self.active_requests[tid]
                    
                    # Indentación sutil si es JSON
                    try:
                        parsed = json.loads(req['resp_body'])
                        req['resp_body'] = json.dumps(parsed, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                    
                    if self.selected_req and self.selected_req['id'] == req['id']:
                        self.root.after(0, lambda: self.show_details(req))
                else:
                    req['resp_body'] += msg

    def add_request_row(self, req):
        # Cada fila es un ctk.CTkFrame oscuro sin bordes redondeados toscos
        row = ctk.CTkFrame(self.list_scroll, fg_color=self.BG_DARK, height=36, corner_radius=0)
        row.pack(fill="x", side="top")
        row.pack_propagate(False)

        # Guardar referencias de widgets para poder ocultarlos o destruirlos
        self.row_widgets[req['id']] = {
            'frame': row,
            'labels': []
        }

        # 1. URL / Name
        name_lbl = ctk.CTkLabel(row, text=req['name'], font=(Theme.FONT, 13, "bold"), text_color=self.TEXT_WHITE, anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True, padx=(10, 4))
        self.row_widgets[req['id']]['name_lbl'] = name_lbl

        # Contenedor único para columnas adicionales (se oculta de un solo golpe en Split View)
        extra_frame = ctk.CTkFrame(row, fg_color="transparent", height=36, corner_radius=0)
        extra_frame.pack(side="left", fill="y")
        self.row_widgets[req['id']]['extra_frame'] = extra_frame

        # 2. Status
        status_lbl = ctk.CTkLabel(extra_frame, text=req['status'], font=(Theme.FONT, 13, "bold"), text_color=self.TEXT_GRAY, width=65, anchor="w")
        status_lbl.pack(side="left", padx=4)
        self.row_widgets[req['id']]['labels'].append((status_lbl, 65))

        # 3. Method (GET/POST)
        method_colors = {"GET": "#4ADE80", "POST": "#C084FC", "PUT": "#FDBA74", "DELETE": "#FCA5A5"}
        m_color = method_colors.get(req['method'], self.TEXT_WHITE)
        method_lbl = ctk.CTkLabel(extra_frame, text=req['method'], font=(Theme.FONT, 13, "bold"), text_color=m_color, width=75, anchor="w")
        method_lbl.pack(side="left", padx=4)
        self.row_widgets[req['id']]['labels'].append((method_lbl, 75))

        # 4. Domain
        domain_lbl = ctk.CTkLabel(extra_frame, text=req['domain'], font=(Theme.FONT, 13), text_color=self.TEXT_GRAY, width=130, anchor="w")
        domain_lbl.pack(side="left", padx=4)
        self.row_widgets[req['id']]['labels'].append((domain_lbl, 130))

        # 5. Type
        type_lbl = ctk.CTkLabel(extra_frame, text=req['type'], font=(Theme.FONT, 13), text_color=self.TEXT_GRAY, width=60, anchor="w")
        type_lbl.pack(side="left", padx=4)
        self.row_widgets[req['id']]['labels'].append((type_lbl, 60))

        # 6. Size
        size_lbl = ctk.CTkLabel(extra_frame, text=req['size'], font=(Theme.FONT, 13), text_color=self.TEXT_GRAY, width=70, anchor="w")
        size_lbl.pack(side="left", padx=4)
        self.row_widgets[req['id']]['labels'].append((size_lbl, 70))

        # 7. Time
        time_lbl = ctk.CTkLabel(extra_frame, text=req['time'], font=(Theme.FONT, 13), text_color=self.TEXT_GRAY, width=90, anchor="w")
        time_lbl.pack(side="left", padx=4)
        self.row_widgets[req['id']]['labels'].append((time_lbl, 90))

        # Eventos para fila
        widgets = [row, name_lbl, status_lbl, method_lbl, domain_lbl, type_lbl, size_lbl, time_lbl, extra_frame]
        for w in widgets:
            w.bind("<Enter>", lambda e, r=row, rid=req['id']: self.on_row_hover(r, rid))
            w.bind("<Leave>", lambda e, r=row, rid=req['id']: self.on_row_leave(r, rid))
            w.bind("<Button-1>", lambda e, rq=req: self.select_request(rq))

        # Si ya hay un elemento seleccionado, esta nueva fila se debe ajustar inmediatamente a vista estrecha
        if self.selected_req is not None:
            self.set_row_view_narrow(req['id'])

        if self.auto_scroll_var.get():
            try:
                self.list_scroll._parent_canvas.yview_moveto(1.0)
            except Exception:
                try:
                    self.list_scroll._canvas.yview_moveto(1.0)
                except Exception:
                    pass

    def update_request_row(self, req):
        w_dict = self.row_widgets.get(req['id'])
        if not w_dict:
            return

        # 2. Status Label (es el primer label de la lista de labels adicionales)
        status = req['status']
        color = "#4ADE80" if status.startswith("2") else ("#EF4444" if status.startswith("4") or status.startswith("5") else "#F59E0B")
        w_dict['labels'][0][0].configure(text=status, text_color=color)

        # 5. Type
        w_dict['labels'][3][0].configure(text=req['type'])

        # 6. Size
        w_dict['labels'][4][0].configure(text=req['size'])

        # 7. Time
        w_dict['labels'][5][0].configure(text=req['time'])

        self.apply_filters()

    def on_row_hover(self, frame, rid):
        if self.selected_req and self.selected_req['id'] == rid:
            return
        frame.configure(fg_color="#1A1A22")

    def on_row_leave(self, frame, rid):
        if self.selected_req and self.selected_req['id'] == rid:
            return
        frame.configure(fg_color=self.BG_DARK)

    def select_request(self, req):
        # Deseleccionar fila anterior
        if self.selected_req:
            old_row = self.row_widgets.get(self.selected_req['id'])
            if old_row:
                old_row['frame'].configure(fg_color=self.BG_DARK)

        self.selected_req = req
        # Colorear fila seleccionada de gris claro/medio de LambdaTest
        row_dict = self.row_widgets.get(req['id'])
        if row_dict:
            row_dict['frame'].configure(fg_color="#22222B")

        # Configurar vista estrecha (Split View)
        self.set_split_view_active(True)
        self.show_details(req)

    def set_split_view_active(self, active):
        if active:
            # 1. Hacemos que el pane izquierdo sea más pequeño
            self.left_pane.configure(width=260)
            self.left_pane.pack_propagate(False)
            self.left_pane.pack_configure(expand=False, fill="both", side="left")
            
            # 2. Ocultamos las cabeceras de la tabla
            self.table_header.pack_forget()
            self.sep_line.pack_forget()

            # 3. Para cada fila, ocultar todas las columnas excepto Name / URL
            for rid in self.row_widgets:
                self.set_row_view_narrow(rid)

            # 4. Mostrar el panel de detalles derecho
            if not self.right_pane.winfo_ismapped():
                self.right_pane.pack(fill="both", expand=True, side="right", padx=(8, 0))
        else:
            # 1. Restauramos tamaño del pane izquierdo
            self.left_pane.pack_propagate(True)
            self.left_pane.pack_configure(expand=True, fill="both", side="left")
            
            # 2. Volvemos a mostrar cabeceras de tabla en el orden correcto
            # Para evitar TclError con los wrappers de CustomTkinter, ocultamos temporalmente
            # la lista scrollable y volvemos a empacar todo en el orden deseado.
            self.table_header.pack_forget()
            self.sep_line.pack_forget()
            self.list_scroll.pack_forget()
            
            self.table_header.pack(fill="x", side="top", pady=(0, 2))
            self.sep_line.pack(fill="x", side="top")
            self.list_scroll.pack(fill="both", expand=True)

            # 3. Restauramos todas las columnas en cada fila
            for rid in self.row_widgets:
                self.set_row_view_wide(rid)

            # 4. Ocultamos panel derecho
            self.right_pane.pack_forget()

    def set_row_view_narrow(self, rid):
        w_dict = self.row_widgets.get(rid)
        if w_dict:
            if 'extra_frame' in w_dict:
                w_dict['extra_frame'].pack_forget()
            w_dict['name_lbl'].pack_configure(fill="x", expand=True)

    def set_row_view_wide(self, rid):
        w_dict = self.row_widgets.get(rid)
        if w_dict:
            w_dict['name_lbl'].pack_forget()
            w_dict['name_lbl'].pack(side="left", fill="x", expand=True, padx=(10, 4))
            if 'extra_frame' in w_dict:
                w_dict['extra_frame'].pack(side="left", fill="y")

    def show_details(self, req):
        # Limpiar panel derecho
        for child in self.right_pane.winfo_children():
            child.destroy()

        # Cabecera superior del panel de detalles
        hdr = ctk.CTkFrame(self.right_pane, fg_color=self.BG_DARK, height=48, corner_radius=0)
        hdr.pack(fill="x", side="top", ipady=2)
        
        # Botón Cerrar - USER ICON PLACEHOLDER: Puedes cambiar el texto "Cerrar ✕" o usar tu propio icono aquí
        ctk.CTkButton(
            hdr, text="Cerrar ✕", width=90, height=30, corner_radius=4,
            fg_color="transparent", hover_color="#222227", text_color=self.TEXT_WHITE,
            border_width=1, border_color=self.BORDER_DARK,
            font=(Theme.FONT, 14, "bold"),
            command=self.hide_details
        ).pack(side="left", padx=(12, 4))

        # Tabs: Headers / Response
        tabs_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        tabs_frame.pack(side="left", padx=8)

        # Tab Headers
        btn_headers = ctk.CTkButton(
            tabs_frame, text="Headers", width=85, height=28, corner_radius=0,
            fg_color="transparent", text_color=self.TEXT_WHITE if self.current_tab == "Headers" else self.TEXT_GRAY,
            font=(Theme.FONT, 14, "bold"),
            command=lambda: self.switch_tab("Headers")
        )
        btn_headers.pack(side="left")
        
        # Pequeña barra inferior naranja en la pestaña seleccionada
        if self.current_tab == "Headers":
            btn_headers.configure(text_color="#FF7A59") # color naranja de LambdaTest active tab

        # Tab Response
        btn_response = ctk.CTkButton(
            tabs_frame, text="Response", width=85, height=28, corner_radius=0,
            fg_color="transparent", text_color=self.TEXT_WHITE if self.current_tab == "Response" else self.TEXT_GRAY,
            font=(Theme.FONT, 14, "bold"),
            command=lambda: self.switch_tab("Response")
        )
        btn_response.pack(side="left", padx=8)
        if self.current_tab == "Response":
            btn_response.configure(text_color="#FF7A59")

        # Botón "Copiar cURL" - USER ICON PLACEHOLDER: Puedes cambiar el texto o usar tu propio icono aquí
        ctk.CTkButton(
            hdr, text="Copiar cURL", width=110, height=30, corner_radius=4,
            fg_color="transparent", hover_color="#222227", text_color=self.TEXT_WHITE,
            border_width=1, border_color=self.BORDER_DARK,
            font=(Theme.FONT, 14, "bold"),
            command=self.copy_curl
        ).pack(side="right", padx=(0, 16))

        # Línea divisoria inferior
        ctk.CTkFrame(self.right_pane, fg_color=self.BORDER_DARK, height=1).pack(fill="x")

        # Contenido
        if self.current_tab == "Headers":
            self.render_headers(req)
        else:
            self.render_response(req)

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        if self.selected_req:
            self.show_details(self.selected_req)

    def render_headers(self, req):
        scroll = ctk.CTkScrollableFrame(self.right_pane, fg_color=self.BG_DARK, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=12)

        def toggle_box(btn, box, fill="x", pady=(8, 0)):
            if getattr(box, "is_visible", True):
                box.pack_forget()
                box.is_visible = False
                txt = btn.cget("text")
                if txt.startswith("▾"):
                    btn.configure(text="▸" + txt[1:])
            else:
                box.pack(fill=fill, pady=pady)
                box.is_visible = True
                txt = btn.cget("text")
                if txt.startswith("▸"):
                    btn.configure(text="▾" + txt[1:])

        # ─── 1. General Section ───
        sec_general = ctk.CTkFrame(scroll, fg_color="transparent")
        sec_general.pack(fill="x", pady=(0, 12))

        btn_general = ctk.CTkButton(
            sec_general, text="▾ General", font=(Theme.FONT, 14, "bold"),
            text_color=self.TEXT_GRAY, fg_color="transparent", hover_color="#1C1C24",
            anchor="w", height=32, corner_radius=4,
            command=lambda: toggle_box(btn_general, gen_box)
        )
        btn_general.pack(fill="x")

        gen_box = ctk.CTkFrame(sec_general, fg_color=self.BG_DARK, corner_radius=0)
        gen_box.pack(fill="x", pady=(8, 0))
        gen_box.is_visible = True

        general_rows = [
            ("Request URL:", req['url']),
            ("Request Method:", req['method']),
            ("Status Code:", req['status']),
            ("Remote Address:", ":80") # Por defecto de la imagen
        ]

        for k, v in general_rows:
            row = ctk.CTkFrame(gen_box, fg_color="transparent")
            row.pack(fill="x", pady=3)
            
            key_lbl = ctk.CTkLabel(row, text=k, font=(Theme.FONT, 14, "bold"), text_color=self.TEXT_WHITE, width=180, anchor="nw")
            key_lbl.pack(side="left", anchor="nw")
            
            # Color especial del Status Code
            color = self.TEXT_WHITE
            if k == "Status Code:":
                color = "#4ADE80" if v.startswith("2") else ("#EF4444" if v.startswith("4") or v.startswith("5") else "#F59E0B")
            
            if k == "Request URL:":
                # Use a borderless, dark-themed CTkTextbox for the URL to avoid layout loops and allow smooth selection
                val_txt = ctk.CTkTextbox(
                    row, font=(Theme.FONT, 13), text_color=color, fg_color=self.INPUT_BG,
                    height=44, border_width=1, border_color=self.BORDER_DARK, corner_radius=4, wrap="char"
                )
                val_txt.pack(side="left", fill="x", expand=True, anchor="nw")
                val_txt.insert("1.0", v)
                val_txt.configure(state="disabled")
            else:
                val_lbl = ctk.CTkLabel(row, text=v, font=(Theme.FONT, 14), text_color=color, justify="left", anchor="nw")
                val_lbl.pack(side="left", fill="x", expand=True, anchor="nw")
                val_lbl.configure(wraplength=320)

        # Divisor
        ctk.CTkFrame(scroll, fg_color=self.BORDER_DARK, height=1).pack(fill="x", pady=12)

        # ─── 2. Response Headers Section ───
        sec_resp = ctk.CTkFrame(scroll, fg_color="transparent")
        sec_resp.pack(fill="x", pady=(0, 12))

        btn_resp = ctk.CTkButton(
            sec_resp, text="▾ Response Headers", font=(Theme.FONT, 14, "bold"),
            text_color=self.TEXT_GRAY, fg_color="transparent", hover_color="#1C1C24",
            anchor="w", height=32, corner_radius=4,
            command=lambda: toggle_box(btn_resp, headers_box)
        )
        btn_resp.pack(fill="x")

        headers_box = ctk.CTkFrame(sec_resp, fg_color=self.BG_DARK, corner_radius=0)
        headers_box.pack(fill="x", pady=(8, 0))
        headers_box.is_visible = True

        if not req['resp_headers']:
            ctk.CTkLabel(headers_box, text="(No headers captured)", font=(Theme.FONT, 14, "italic"), text_color=self.TEXT_GRAY).pack(anchor="w", pady=4)
        else:
            # Parse and sort response headers alphabetically by key
            resp_headers_parsed = []
            for h in req['resp_headers']:
                if ":" in h:
                    k, v = h.split(":", 1)
                    resp_headers_parsed.append((k.strip(), v.strip()))
            resp_headers_parsed.sort(key=lambda x: x[0].lower())

            for k, v in resp_headers_parsed:
                is_token = "token" in k.lower() or "authorization" in k.lower() or len(v) > 150
                if is_token:
                    # Token Block
                    token_frame = ctk.CTkFrame(headers_box, fg_color="transparent")
                    token_frame.pack(fill="x", pady=6)
                    
                    # Top row: title left, copy button right
                    top_bar = ctk.CTkFrame(token_frame, fg_color="transparent")
                    top_bar.pack(fill="x")
                    
                    title_lbl = ctk.CTkLabel(top_bar, text=k + ":", font=(Theme.FONT, 14, "bold"), text_color=self.TEXT_GRAY)
                    title_lbl.pack(side="left")
                    
                    copy_btn = ctk.CTkButton(
                        top_bar, text="📋 Copiar", width=70, height=24, corner_radius=4,
                        fg_color="#222227", hover_color="#2D2D35", text_color=self.TEXT_WHITE,
                        font=(Theme.FONT, 12, "bold"),
                        command=lambda val=v: self.copy_to_clipboard(val)
                    )
                    copy_btn.pack(side="right")
                    
                    # Accordion toggle button
                    accordion_btn = ctk.CTkButton(
                        token_frame, text="▸ Mostrar contenido", font=(Theme.FONT, 13, "bold"),
                        text_color=self.TEXT_GRAY, fg_color="transparent", hover_color="#1C1C24",
                        anchor="w", height=24, corner_radius=4
                    )
                    accordion_btn.pack(fill="x", pady=(4, 0))
                    
                    # Textbox inside box (starts hidden)
                    token_box = ctk.CTkFrame(token_frame, fg_color=self.BG_DARK, corner_radius=4, border_width=1, border_color=self.BORDER_DARK)
                    token_box.is_visible = False
                    
                    token_txt = ctk.CTkTextbox(
                        token_box, font=("Consolas", 13),
                        fg_color=self.BG_DARK, text_color="#FF7A59",
                        height=80, corner_radius=4, wrap="char"
                    )
                    token_txt.pack(fill="both", expand=True, padx=4, pady=4)
                    token_txt.insert("1.0", v)
                    token_txt.configure(state="disabled")
                    
                    # Configure toggle action
                    def make_toggle(btn=accordion_btn, box=token_box):
                        def toggle_token():
                            if box.is_visible:
                                box.pack_forget()
                                box.is_visible = False
                                btn.configure(text="▸ Mostrar contenido")
                            else:
                                box.pack(fill="x", pady=(4, 0))
                                box.is_visible = True
                                btn.configure(text="▾ Ocultar contenido")
                        return toggle_token
                            
                    accordion_btn.configure(command=make_toggle(accordion_btn, token_box))
                else:
                    row = ctk.CTkFrame(headers_box, fg_color="transparent")
                    row.pack(fill="x", pady=3)
                    
                    key_lbl = ctk.CTkLabel(row, text=k + ":", font=(Theme.FONT, 14, "bold"), text_color=self.TEXT_GRAY, width=180, anchor="nw")
                    key_lbl.pack(side="left", anchor="nw")
                    
                    val_lbl = ctk.CTkLabel(row, text=v, font=(Theme.FONT, 14), text_color=self.TEXT_WHITE, justify="left", anchor="nw")
                    val_lbl.pack(side="left", fill="x", expand=True, anchor="nw")
                    val_lbl.configure(wraplength=320)

        # Divisor
        ctk.CTkFrame(scroll, fg_color=self.BORDER_DARK, height=1).pack(fill="x", pady=12)

        # ─── 3. Request Headers Section ───
        sec_req = ctk.CTkFrame(scroll, fg_color="transparent")
        sec_req.pack(fill="x", pady=(0, 12))

        btn_req = ctk.CTkButton(
            sec_req, text="▾ Request Headers", font=(Theme.FONT, 14, "bold"),
            text_color=self.TEXT_GRAY, fg_color="transparent", hover_color="#1C1C24",
            anchor="w", height=32, corner_radius=4,
            command=lambda: toggle_box(btn_req, req_headers_box)
        )
        btn_req.pack(fill="x")

        req_headers_box = ctk.CTkFrame(sec_req, fg_color=self.BG_DARK, corner_radius=0)
        req_headers_box.pack(fill="x", pady=(8, 0))
        req_headers_box.is_visible = True

        if not req['req_headers']:
            ctk.CTkLabel(req_headers_box, text="(No request headers captured)", font=(Theme.FONT, 14, "italic"), text_color=self.TEXT_GRAY).pack(anchor="w", pady=4)
        else:
            # Parse and sort request headers alphabetically by key
            req_headers_parsed = []
            for h in req['req_headers']:
                if ":" in h:
                    k, v = h.split(":", 1)
                    req_headers_parsed.append((k.strip(), v.strip()))
            req_headers_parsed.sort(key=lambda x: x[0].lower())

            for k, v in req_headers_parsed:
                is_token = "token" in k.lower() or "authorization" in k.lower() or len(v) > 150
                if is_token:
                    # Token Block
                    token_frame = ctk.CTkFrame(req_headers_box, fg_color="transparent")
                    token_frame.pack(fill="x", pady=6)
                    
                    # Top row: title left, copy button right
                    top_bar = ctk.CTkFrame(token_frame, fg_color="transparent")
                    top_bar.pack(fill="x")
                    
                    title_lbl = ctk.CTkLabel(top_bar, text=k + ":", font=(Theme.FONT, 14, "bold"), text_color=self.TEXT_GRAY)
                    title_lbl.pack(side="left")
                    
                    copy_btn = ctk.CTkButton(
                        top_bar, text="📋 Copiar", width=70, height=24, corner_radius=4,
                        fg_color="#222227", hover_color="#2D2D35", text_color=self.TEXT_WHITE,
                        font=(Theme.FONT, 12, "bold"),
                        command=lambda val=v: self.copy_to_clipboard(val)
                    )
                    copy_btn.pack(side="right")
                    
                    # Accordion toggle button
                    accordion_btn = ctk.CTkButton(
                        token_frame, text="▸ Mostrar contenido", font=(Theme.FONT, 13, "bold"),
                        text_color=self.TEXT_GRAY, fg_color="transparent", hover_color="#1C1C24",
                        anchor="w", height=24, corner_radius=4
                    )
                    accordion_btn.pack(fill="x", pady=(4, 0))
                    
                    # Textbox inside box (starts hidden)
                    token_box = ctk.CTkFrame(token_frame, fg_color=self.BG_DARK, corner_radius=4, border_width=1, border_color=self.BORDER_DARK)
                    token_box.is_visible = False
                    
                    token_txt = ctk.CTkTextbox(
                        token_box, font=("Consolas", 13),
                        fg_color=self.BG_DARK, text_color="#FF7A59",
                        height=80, corner_radius=4, wrap="char"
                    )
                    token_txt.pack(fill="both", expand=True, padx=4, pady=4)
                    token_txt.insert("1.0", v)
                    token_txt.configure(state="disabled")
                    
                    # Configure toggle action
                    def make_toggle(btn=accordion_btn, box=token_box):
                        def toggle_token():
                            if box.is_visible:
                                box.pack_forget()
                                box.is_visible = False
                                btn.configure(text="▸ Mostrar contenido")
                            else:
                                box.pack(fill="x", pady=(4, 0))
                                box.is_visible = True
                                btn.configure(text="▾ Ocultar contenido")
                        return toggle_token
                            
                    accordion_btn.configure(command=make_toggle(accordion_btn, token_box))
                else:
                    row = ctk.CTkFrame(req_headers_box, fg_color="transparent")
                    row.pack(fill="x", pady=3)
                    
                    key_lbl = ctk.CTkLabel(row, text=k + ":", font=(Theme.FONT, 14, "bold"), text_color=self.TEXT_GRAY, width=180, anchor="nw")
                    key_lbl.pack(side="left", anchor="nw")
                    
                    val_lbl = ctk.CTkLabel(row, text=v, font=(Theme.FONT, 14), text_color=self.TEXT_WHITE, justify="left", anchor="nw")
                    val_lbl.pack(side="left", fill="x", expand=True, anchor="nw")
                    val_lbl.configure(wraplength=320)

        # ─── 4. Request Payload Section ───
        if req['req_body'].strip():
            ctk.CTkFrame(scroll, fg_color=self.BORDER_DARK, height=1).pack(fill="x", pady=12)

            sec_payload = ctk.CTkFrame(scroll, fg_color="transparent")
            sec_payload.pack(fill="x", pady=(0, 12))

            btn_payload = ctk.CTkButton(
                sec_payload, text="▾ Request Payload", font=(Theme.FONT, 14, "bold"),
                text_color=self.TEXT_GRAY, fg_color="transparent", hover_color="#1C1C24",
                anchor="w", height=32, corner_radius=4,
                command=lambda: toggle_box(btn_payload, payload_box)
            )
            btn_payload.pack(fill="x")

            payload_box = ctk.CTkFrame(sec_payload, fg_color=self.BG_DARK, corner_radius=4, border_width=1, border_color=self.BORDER_DARK)
            payload_box.pack(fill="x", pady=(8, 0))
            payload_box.is_visible = True

            payload_txt = ctk.CTkTextbox(
                payload_box, font=("Consolas", 15),
                fg_color=self.BG_DARK, text_color="#FF7A59",
                height=150, corner_radius=4, wrap="word"
            )
            payload_txt.pack(fill="both", expand=True)
            payload_txt.insert("1.0", req['req_body'].strip())
            payload_txt.configure(state="disabled")

    def render_response(self, req):
        container = ctk.CTkFrame(self.right_pane, fg_color=self.BG_DARK, corner_radius=0)
        container.pack(fill="both", expand=True, padx=16, pady=12)

        body = req['resp_body'].strip()
        is_json = False
        parsed_json = None
        
        # Límite de seguridad para evitar cuelgues del hilo principal en respuestas JSON masivas
        MAX_JSON_TREE_SIZE = 150 * 1024  # 150 KB
        is_too_large = len(body) > MAX_JSON_TREE_SIZE
        
        if body and not is_too_large:
            try:
                parsed_json = json.loads(body)
                is_json = True
            except Exception:
                pass

        if is_json:
            # Top control bar for switching views and actions
            control_bar = ctk.CTkFrame(container, fg_color="transparent", height=32)
            control_bar.pack(fill="x", side="top", pady=(0, 6))

            # We will use two frames to hold the actual views:
            tree_frame = ctk.CTkFrame(container, fg_color="transparent")
            raw_frame = ctk.CTkFrame(container, fg_color="transparent")
            
            # Pack default view
            tree_frame.pack(fill="both", expand=True)

            # Configure Treeview Style
            import tkinter.ttk as ttk
            style = ttk.Style()
            try:
                style.theme_use("clam")
            except Exception:
                pass
            style.configure("Custom.Treeview",
                            background="#0F0F12",
                            foreground="#FFFFFF",
                            fieldbackground="#0F0F12",
                            rowheight=26,
                            font=("Consolas", 11),
                            borderwidth=0,
                            highlightthickness=0)
            style.map("Custom.Treeview",
                      background=[('selected', '#22222B')],
                      foreground=[('selected', '#FFFFFF')])

            # Configure Scrollbar Styles for dark theme
            style.configure(
                "Custom.Vertical.TScrollbar",
                background="#222227", troughcolor="#0F0F12",
                borderwidth=0, width=8, arrowsize=0, relief="flat"
            )
            style.map(
                "Custom.Vertical.TScrollbar",
                background=[("active", "#3E3E47"), ("!active", "#222227")]
            )
            style.layout(
                "Custom.Vertical.TScrollbar",
                [("Vertical.Scrollbar.trough", {
                    "sticky": "ns",
                    "children": [("Vertical.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})]
                })]
            )

            style.configure(
                "Custom.Horizontal.TScrollbar",
                background="#222227", troughcolor="#0F0F12",
                borderwidth=0, width=8, arrowsize=0, relief="flat"
            )
            style.map(
                "Custom.Horizontal.TScrollbar",
                background=[("active", "#3E3E47"), ("!active", "#222227")]
            )
            style.layout(
                "Custom.Horizontal.TScrollbar",
                [("Horizontal.Scrollbar.trough", {
                    "sticky": "ew",
                    "children": [("Horizontal.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})]
                })]
            )

            # Actions frame (Expand / Collapse)
            actions_frame = ctk.CTkFrame(control_bar, fg_color="transparent")
            actions_frame.pack(side="right")

            # Switch view command
            def select_sub_view(view_name):
                if view_name == "tree":
                    raw_frame.pack_forget()
                    tree_frame.pack(fill="both", expand=True)
                    btn_tree.configure(fg_color="#3E3E47", text_color="#FFFFFF")
                    btn_raw.configure(fg_color="#222227", text_color="#A0A0A5")
                    actions_frame.pack(side="right")
                else:
                    tree_frame.pack_forget()
                    raw_frame.pack(fill="both", expand=True)
                    btn_tree.configure(fg_color="#222227", text_color="#A0A0A5")
                    btn_raw.configure(fg_color="#3E3E47", text_color="#FFFFFF")
                    actions_frame.pack_forget()

            btn_tree = ctk.CTkButton(
                control_bar, text="JSON Tree", width=80, height=26, corner_radius=4,
                fg_color="#3E3E47", hover_color="#2D2D35", text_color="#FFFFFF",
                font=(Theme.FONT, 12, "bold"),
                command=lambda: select_sub_view("tree")
            )
            btn_tree.pack(side="left", padx=(0, 4))

            btn_raw = ctk.CTkButton(
                control_bar, text="Texto Plano", width=80, height=26, corner_radius=4,
                fg_color="#222227", hover_color="#2D2D35", text_color="#A0A0A5",
                font=(Theme.FONT, 12, "bold"),
                command=lambda: select_sub_view("raw")
            )
            btn_raw.pack(side="left")

            # Tree Layout using native ttk.Scrollbar styled for dark theme to prevent recursion
            scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", style="Custom.Horizontal.TScrollbar")
            scroll_x.pack(side="bottom", fill="x", pady=(2, 0))

            tree_container = ctk.CTkFrame(tree_frame, fg_color="#0F0F12", border_width=1, border_color=self.BORDER_DARK, corner_radius=4)
            tree_container.pack(fill="both", expand=True)

            tree = ttk.Treeview(tree_container, style="Custom.Treeview", show="tree")
            tree.pack(side="left", fill="both", expand=True, padx=2, pady=2)

            scroll_y = ttk.Scrollbar(tree_container, orient="vertical", command=tree.yview, style="Custom.Vertical.TScrollbar")
            scroll_y.pack(side="right", fill="y")
            
            scroll_x.configure(command=tree.xview)
            tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

            # Recursive populator
            def populate_node(parent_id, val):
                if isinstance(val, dict):
                    keys = list(val.keys())
                    limit = 150
                    for k in keys[:limit]:
                        v = val[k]
                        if isinstance(v, (dict, list)):
                            child_count = len(v)
                            type_char = "{}" if isinstance(v, dict) else "[]"
                            node_text = f"{k}: {type_char} ({child_count} items)"
                            node_id = tree.insert(parent_id, "end", text=node_text, open=False)
                            populate_node(node_id, v)
                        else:
                            v_str = json.dumps(v, ensure_ascii=False)
                            if len(v_str) > 200:
                                v_str = v_str[:200] + "... [truncado]"
                            node_text = f"{k}: {v_str}"
                            tree.insert(parent_id, "end", text=node_text)
                    if len(keys) > limit:
                        tree.insert(parent_id, "end", text=f"... (y {len(keys) - limit} campos más)")
                elif isinstance(val, list):
                    limit = 150
                    for i, v in enumerate(val[:limit]):
                        if isinstance(v, (dict, list)):
                            child_count = len(v)
                            type_char = "{}" if isinstance(v, dict) else "[]"
                            node_text = f"[{i}]: {type_char} ({child_count} items)"
                            node_id = tree.insert(parent_id, "end", text=node_text, open=False)
                            populate_node(node_id, v)
                        else:
                            v_str = json.dumps(v, ensure_ascii=False)
                            if len(v_str) > 200:
                                v_str = v_str[:200] + "... [truncado]"
                            node_text = f"[{i}]: {v_str}"
                            tree.insert(parent_id, "end", text=node_text)
                    if len(val) > limit:
                        tree.insert(parent_id, "end", text=f"... (y {len(val) - limit} elementos más)")

            # Populate
            if isinstance(parsed_json, (dict, list)):
                populate_node("", parsed_json)
            else:
                v_str = json.dumps(parsed_json, ensure_ascii=False)
                if len(v_str) > 200:
                    v_str = v_str[:200] + "... [truncado]"
                tree.insert("", "end", text=v_str)

            # Expand / Collapse handlers
            def expand_all():
                def recurse(node):
                    tree.item(node, open=True)
                    for child in tree.get_children(node):
                        recurse(child)
                for node in tree.get_children(""):
                    recurse(node)

            def collapse_all():
                def recurse(node):
                    tree.item(node, open=False)
                    for child in tree.get_children(node):
                        recurse(child)
                for node in tree.get_children(""):
                    recurse(node)

            btn_expand = ctk.CTkButton(
                actions_frame, text="💥 Expandir todo", width=94, height=26, corner_radius=4,
                fg_color="#222227", hover_color="#2D2D35", text_color="#FFFFFF",
                font=(Theme.FONT, 11, "bold"),
                command=expand_all
            )
            btn_expand.pack(side="left", padx=(0, 4))

            btn_collapse = ctk.CTkButton(
                actions_frame, text="💤 Colapsar todo", width=94, height=26, corner_radius=4,
                fg_color="#222227", hover_color="#2D2D35", text_color="#FFFFFF",
                font=(Theme.FONT, 11, "bold"),
                command=collapse_all
            )
            btn_collapse.pack(side="left")

            # Raw view layout inside raw_frame
            textbox = ctk.CTkTextbox(
                raw_frame, font=("Consolas", 15),
                fg_color=self.BG_DARK, text_color="#4ADE80",
                corner_radius=4, border_width=1, border_color=self.BORDER_DARK,
                wrap="word"
            )
            textbox.pack(fill="both", expand=True)
            textbox.insert("1.0", body)
            textbox.configure(state="disabled")

        else:
            # Fallback for non-JSON content or large payloads
            textbox = ctk.CTkTextbox(
                container, font=("Consolas", 15),
                fg_color=self.BG_DARK, text_color="#4ADE80",
                corner_radius=4, border_width=1, border_color=self.BORDER_DARK,
                wrap="word"
            )
            textbox.pack(fill="both", expand=True)

            if not body:
                if req['state'] == 'requesting':
                    textbox.insert("1.0", "(Petición en curso...)")
                else:
                    textbox.insert("1.0", "(No response body returned)")
            else:
                if is_too_large:
                    warning_msg = f"⚠️ Payload de respuesta grande ({len(body)/1024:.1f} KB).\n"
                    warning_msg += "El visor de árbol JSON se deshabilitó para asegurar el rendimiento.\n\n"
                    textbox.insert("1.0", warning_msg + body)
                else:
                    textbox.insert("1.0", body)
            
            textbox.configure(state="disabled")

    def hide_details(self):
        # Quitar selección gráfica
        if self.selected_req:
            row_dict = self.row_widgets.get(self.selected_req['id'])
            if row_dict:
                row_dict['frame'].configure(fg_color=self.BG_DARK)
            self.selected_req = None

        # Desactivar Split View
        self.set_split_view_active(False)

    def copy_curl(self):
        if not self.selected_req:
            return
        req = self.selected_req
        
        parts = ["curl", "--location"]
        parts.append(f"'{req['url']}'")
        parts.append(f"-X {req['method']}")
        
        # Analizar cabeceras de petición
        has_user_agent = False
        has_accept_encoding = False
        
        for h in req['req_headers']:
            if ":" in h:
                parts.append(f"-H '{h.strip()}'")
                h_lower = h.lower()
                if h_lower.startswith("user-agent:"):
                    has_user_agent = True
                if h_lower.startswith("accept-encoding:"):
                    has_accept_encoding = True
                    
        # Agregar headers de simulación Android si faltan
        if not has_user_agent:
            parts.append("-H 'user-agent: okhttp/4.12.0'")
        if not has_accept_encoding:
            parts.append("-H 'accept-encoding: gzip'")
            
        # Siempre agregar comprimido
        parts.append("--compressed")
                
        # Agregar cuerpo si existe
        if req['req_body'].strip():
            escaped_body = req['req_body'].strip().replace("'", "'\\''")
            parts.append(f"-d '{escaped_body}'")
            
        curl_cmd = " \\\n  ".join(parts)
        self.copy_to_clipboard(curl_cmd)

    def copy_to_clipboard(self, text):
        self.win.clipboard_clear()
        self.win.clipboard_append(text)
        
        # Pequeña notificación de copiado en el título temporal de la ventana
        self.win.title("✔ Copiado al portapapeles - Network Logs")
        self.win.after(1200, lambda: self.win.title("Network Logs - LambdaTest Copy"))

    def apply_filters(self):
        query = self.search_entry.get().strip().lower()
        errors_only = self.errors_only_var.get()
        show_connect = self.show_connect_var.get()

        for req in self.requests:
            w_dict = self.row_widgets.get(req['id'])
            if not w_dict:
                continue

            # 1. Filtro por píldoras (All, JS, CSS, Img, Media, Font, Doc, WS)
            pill_match = True
            if self.active_filter != "All":
                t = req['type'].lower()
                if self.active_filter == "JS" and t != "js": pill_match = False
                elif self.active_filter == "CSS" and t != "css": pill_match = False
                elif self.active_filter == "Img" and t not in ["png", "jpeg", "jpg", "gif", "webp", "svg", "ico", "bmp", "image"]: pill_match = False
                elif self.active_filter == "Media" and t not in ["mp4", "mp3", "ogg", "webm", "media"]: pill_match = False
                elif self.active_filter == "Font" and t not in ["woff", "woff2", "ttf", "otf", "eot", "font"]: pill_match = False
                elif self.active_filter == "Doc" and t not in ["doc", "docx", "json", "pdf", "xls", "xlsx", "doc"]: pill_match = False
                elif self.active_filter == "WS" and t != "ws": pill_match = False

            # 2. Filtro búsqueda URL
            search_match = True
            if query:
                if query not in req['url'].lower() and query not in req['name'].lower() and query not in req['domain'].lower():
                    search_match = False

            # 3. Filtro Errors Only
            errors_match = True
            if errors_only:
                status = req['status']
                if status == '...' or (not status.startswith("4") and not status.startswith("5")):
                    errors_match = False

            if pill_match and search_match and errors_match:
                w_dict['frame'].pack(fill="x", side="top")
            else:
                w_dict['frame'].pack_forget()

    def clear_logs(self):
        self.hide_details()
        for rid in list(self.row_widgets.keys()):
            self.row_widgets[rid]['frame'].destroy()
        self.requests.clear()
        self.active_requests.clear()
        self.row_widgets.clear()

    def append_log_direct(self, text, tag):
        print(f"[NetworkLogs] {text}")

    def download_logs(self):
        from tkinter import filedialog
        try:
            file_path = filedialog.asksaveasfilename(
                title="Exportar Network Logs",
                defaultextension=".json",
                filetypes=[("Archivos JSON", "*.json")]
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.requests, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def on_close(self):
        self.stop_capture()
        try:
            self.win.destroy()
        except Exception:
            pass

def show(root):
    """Lanza la ventana de logs de red de LambdaTest."""
    LogViewerWindow(root)
