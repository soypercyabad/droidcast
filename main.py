# ══════════════════════════════════════════════════════════════════════════════
# main.py — Punto de entrada de la aplicación
# ══════════════════════════════════════════════════════════════════════════════

import logging

from app.ui.main_window import start

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )
    start()
