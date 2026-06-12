# ══════════════════════════════════════════════════════════════════════════════
# app/core/screenshot.py — Captura de pantalla del dispositivo Android
# ══════════════════════════════════════════════════════════════════════════════

import ctypes
import io
import logging
import os
import subprocess

from PIL import Image

from app.core.adb import get_adb_path

logger = logging.getLogger(__name__)

# Ruta al marco de teléfono (relativa a BASE_DIR)
_FRAME_FILENAME = os.path.join("assets", "phone.png")


# ── Captura raw ───────────────────────────────────────────────────────────────

def capture_raw() -> bytes | None:
    """
    Captura la pantalla del dispositivo mediante 'adb exec-out screencap -p'.
    Retorna los bytes PNG crudos, o None si la captura falla.
    """
    try:
        adb_path = get_adb_path()
        result = subprocess.run(
            [adb_path, "exec-out", "screencap", "-p"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        err = result.stderr.decode("utf-8", errors="ignore") if result.stderr else "sin detalle"
        logger.error(f"screencap falló (code={result.returncode}): {err}")
        return None
    except subprocess.TimeoutExpired:
        logger.error("screencap: tiempo de espera agotado")
        return None
    except Exception as e:
        logger.error(f"Error en capture_raw: {e}")
        return None


# ── Marco de teléfono ─────────────────────────────────────────────────────────

def _apply_phone_frame(screenshot: Image.Image, frame_path: str) -> Image.Image:
    try:
        frame = Image.open(frame_path).convert("RGBA")
        sw, sh = screenshot.size
        
        # Coordenadas exactas del área transparente (pantalla) en assets/phone.png
        # Obtenidas mediante análisis de píxeles: Hole empieza en (14, 17) con tamaño 575x1247
        hole_w = 575
        hole_h = 1247
        
        # Calculamos cuánto hay que escalar el marco para que su "agujero"
        # mida exactamente lo mismo que el screenshot.
        scale_x = sw / hole_w
        scale_y = sh / hole_h
        
        new_fw = int(frame.width * scale_x)
        new_fh = int(frame.height * scale_y)
        
        # Estiramos el marco (incluyendo sus bordes)
        frame_s = frame.resize((new_fw, new_fh), Image.LANCZOS)
        
        # Calculamos dónde empieza el agujero en el marco ya escalado
        off_x = int(14 * scale_x)
        off_y = int(17 * scale_y)
        
        # Lienzo del tamaño total del marco con fondo totalmente transparente
        canvas = Image.new("RGBA", (new_fw, new_fh), (0, 0, 0, 0))
        
        # Pegamos la captura original (intacta, 100% de píxeles) justo en el agujero
        canvas.paste(screenshot.convert("RGBA"), (off_x, off_y))
        
        # Superponemos el marco para que los bordes redondeados y biseles tapen las esquinas
        # Y retornamos en formato RGBA para mantener la transparencia
        return Image.alpha_composite(canvas, frame_s)
    except Exception as e:
        logger.warning(f"Marco no aplicado: {e}")
        return screenshot.convert("RGBA")


# ── Copiar imagen al portapapeles de Windows ──────────────────────────────────

def _copy_image_to_clipboard(image: Image.Image) -> None:
    """
    Copia un PIL Image al portapapeles de Windows conservando la transparencia.
    Inserta tanto CF_DIB (fondo blanco fallback) como CF_PNG (transparente).
    """
    k32 = ctypes.windll.kernel32
    u32 = ctypes.windll.user32

    # 1. Preparar DIB (Fallback sin transparencia, fondo blanco)
    buf_dib = io.BytesIO()
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        bg = Image.new("RGB", image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[-1])
    else:
        bg = image.convert("RGB")
    bg.save(buf_dib, "BMP")
    dib_data = buf_dib.getvalue()[14:]  # Quitar cabecera BITMAPFILEHEADER
    buf_dib.close()

    # 2. Preparar PNG (Con transparencia real)
    buf_png = io.BytesIO()
    image.save(buf_png, "PNG")
    png_data = buf_png.getvalue()
    buf_png.close()

    CF_DIB = 8
    
    # IMPORTANTE: Definir argtypes para que ctypes convierta el string a UTF-16 correctamente
    u32.RegisterClipboardFormatW.restype = ctypes.c_uint
    u32.RegisterClipboardFormatW.argtypes = [ctypes.c_wchar_p]
    
    # Registrar los formatos que usan las apps modernas para transparencia
    CF_PNG = u32.RegisterClipboardFormatW("PNG")
    CF_IMAGE_PNG = u32.RegisterClipboardFormatW("image/png")

    k32.GlobalAlloc.restype  = ctypes.c_void_p
    k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    k32.GlobalLock.restype   = ctypes.c_void_p
    k32.GlobalLock.argtypes  = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]

    u32.OpenClipboard.argtypes   = [ctypes.c_void_p]
    u32.SetClipboardData.restype  = ctypes.c_void_p
    u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]

    # Asignar DIB
    h_mem_dib = k32.GlobalAlloc(0x0002, len(dib_data))
    ptr_dib = k32.GlobalLock(h_mem_dib)
    ctypes.memmove(ptr_dib, dib_data, len(dib_data))
    k32.GlobalUnlock(h_mem_dib)

    # Asignar PNG
    h_mem_png = k32.GlobalAlloc(0x0002, len(png_data))
    if h_mem_png:
        ptr_png = k32.GlobalLock(h_mem_png)
        ctypes.memmove(ptr_png, png_data, len(png_data))
        k32.GlobalUnlock(h_mem_png)
        
    # Asignar image/png (copia adicional porque el sistema toma propiedad de la memoria)
    h_mem_image_png = k32.GlobalAlloc(0x0002, len(png_data))
    if h_mem_image_png:
        ptr_image_png = k32.GlobalLock(h_mem_image_png)
        ctypes.memmove(ptr_image_png, png_data, len(png_data))
        k32.GlobalUnlock(h_mem_image_png)

    if not u32.OpenClipboard(None):
        raise RuntimeError("No se pudo abrir el portapapeles.")
    try:
        u32.EmptyClipboard()
        u32.SetClipboardData(CF_DIB, h_mem_dib)
        if CF_PNG and h_mem_png:
            u32.SetClipboardData(CF_PNG, h_mem_png)
        if CF_IMAGE_PNG and h_mem_image_png:
            u32.SetClipboardData(CF_IMAGE_PNG, h_mem_image_png)
    finally:
        u32.CloseClipboard()


# ── API pública ───────────────────────────────────────────────────────────────

def capture_to_clipboard(with_phone_frame: bool = False) -> tuple[bool, str]:
    """
    Captura la pantalla del dispositivo y copia la imagen al portapapeles.
    No guarda ningún archivo en disco ni en el teléfono.

    Args:
        with_phone_frame: si True, superpone el marco assets/phone.png.

    Retorna:
        (True, "")             en éxito
        (False, mensaje_error) si algo falla
    """
    raw = capture_raw()
    if raw is None:
        return False, "No se pudo capturar la pantalla del dispositivo."

    try:
        screenshot = Image.open(io.BytesIO(raw))
    except Exception as e:
        return False, f"Error al procesar la imagen: {e}"

    if with_phone_frame:
        from app.config import ASSETS_DIR
        frame_path = os.path.join(ASSETS_DIR, "assets", "phone.png")
        image = _apply_phone_frame(screenshot, frame_path)
    else:
        image = screenshot.convert("RGB")

    try:
        _copy_image_to_clipboard(image)
        logger.info("Captura copiada al portapapeles" +
                    (" (con marco)" if with_phone_frame else ""))
        return True, ""
    except Exception as e:
        logger.error(f"Error al copiar al portapapeles: {e}")
        return False, f"Error al copiar al portapapeles: {e}"


def capture_to_file(filepath: str) -> tuple[bool, str]:
    """
    Captura la pantalla y guarda el PNG en *filepath*.

    Retorna:
        (True, "")            en éxito
        (False, mensaje_error) si algo falla
    """
    data = capture_raw()
    if data is None:
        return False, "No se pudo capturar la pantalla del dispositivo."
    try:
        with open(filepath, "wb") as f:
            f.write(data)
        logger.info(f"Captura guardada en: {filepath}")
        return True, ""
    except IOError as e:
        logger.error(f"Error al guardar captura: {e}")
        return False, str(e)
