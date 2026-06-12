# ══════════════════════════════════════════════════════════════════════════════
# app/theme.py — Paleta de colores y tipografía
# ══════════════════════════════════════════════════════════════════════════════


class Theme:
    """Tokens de diseño para modo claro profesional (Figma)."""

    # ── Fondos ────────────────────────────────────────────────────────────────
    BG        = "#F0F2F5"   # fondo general gris claro
    CARD      = "#FFFFFF"   # fondo de tarjetas
    INPUT_BG  = "#FFFFFF"   # fondo de inputs

    # ── Acentos ───────────────────────────────────────────────────────────────
    PURPLE        = "#7C3AED"
    PURPLE_HOVER  = "#6D28D9"
    BLUE          = "#2563EB"
    BLUE_HOVER    = "#1D4ED8"
    TEAL          = "#0D9488"   # botón instalar APK
    TEAL_HOVER    = "#0F766E"
    ORANGE        = "#EA580C"
    ORANGE_HOVER  = "#C2410C"

    # ── Botones modo oscuro (iconos del dispositivo) ───────────────────────────
    NAVY          = "#0F172A"   # fondo oscuro de btn_android
    NAVY_HOVER    = "#1E293B"
    INDIGO        = "#231a6b"   # fondo oscuro btn_code (logs)
    INDIGO_HOVER  = "#42388a"

    # ── Texto ─────────────────────────────────────────────────────────────────
    TEXT       = "#1E293B"
    TEXT_SEC   = "#475569"
    TEXT_MUTED = "#535b66"
    WHITE      = "#FFFFFF"

    # ── Estado ────────────────────────────────────────────────────────────────
    GREEN      = "#16A34A"
    RED        = "#DC2626"
    RED_HOVER  = "#B91C1C"

    # ── Bordes ────────────────────────────────────────────────────────────────
    BORDER     = "#E2E8F0"

    # ── Cuadro de ayuda / hint WiFi (azul claro) ─────────────────────────────
    HINT_BG     = "#EFF6FF"  # fondo azul muy claro
    HINT_BORDER = "#BFDBFE"  # borde azul claro
    HINT_TEXT   = "#1E40AF"  # texto azul oscuro

    # ── Botones auxiliares (carpeta, refresh) ─────────────────────────────────
    BTN_LIGHT      = "#F1F5F9"
    BTN_LIGHT_HVR  = "#E2E8F0"

    # ── Treeview ──────────────────────────────────────────────────────────────
    TREE_SELECT_BG  = "#EDE9FE"  # fondo fila seleccionada
    TREE_SELECT_FG  = "#7C3AED"  # texto fila seleccionada

    # ── Fuente ────────────────────────────────────────────────────────────────
    FONT = "Segoe UI"
