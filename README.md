<p align="center">
  <img src="assets/robot.ico" width="80" alt="DroidCast Logo"/>
</p>

<h1 align="center">DroidCast</h1>

<p align="center">
  <b>Conecta, transmite y gestiona tu dispositivo Android desde tu PC</b><br>
  <sub>by <a href="https://github.com/soypercyabad">@soypercyabad</a></sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-blue?logo=windows" alt="Platform"/>
  <img src="https://img.shields.io/badge/python-3.10+-green?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-purple" alt="License"/>
  <img src="https://img.shields.io/github/v/release/soypercyabad/droidcast?label=release&color=teal" alt="Release"/>
</p>

---

## ¿Qué es DroidCast?

DroidCast es una herramienta de escritorio para Windows que te permite:

- 📱 **Conectar** tu dispositivo Android por Wi-Fi (ADB wireless)
- 🖥️ **Transmitir** la pantalla de tu celular en tiempo real (scrcpy)
- 📦 **Instalar APKs** directamente desde tu PC
- 🔄 **Actualización automática** de scrcpy desde GitHub

Todo desde una interfaz moderna y fácil de usar, sin necesidad de usar la terminal.

---

## Capturas

> _Próximamente_

---

## Instalación

### Opción 1: Ejecutable (recomendado)

1. Ve a [**Releases**](https://github.com/soypercyabad/droidcast/releases)
2. Descarga `DroidCast.exe`
3. Ejecuta. ¡Listo!

### Opción 2: Desde el código fuente

```bash
# Clonar el repositorio
git clone https://github.com/soypercyabad/droidcast.git
cd droidcast

# Instalar dependencias
pip install customtkinter pillow requests

# Ejecutar
python main.py
```

---

## Requisitos previos (en tu celular)

1. Activar **Opciones de Desarrollador**:
   - Ajustes → Acerca del teléfono → toca "Número de compilación" 7 veces
2. Activar en Opciones de desarrollador:
   - ✅ Depuración USB
   - ✅ Instalar vía USB
   - ✅ Depuración USB (Ajustes de seguridad) _(solo Xiaomi/Redmi/POCO)_
3. Conectar por cable USB la primera vez y aceptar la autorización

---

## Uso

1. **Conectar:** Ingresa la IP y puerto de tu dispositivo → presiona "Conectar"
2. **Transmitir:** Presiona "▶ Trasmitir" para ver la pantalla de tu celular
3. **Instalar APK:** Selecciona una carpeta con APKs → elige el archivo → "Instalar APK"

---

## Estructura del proyecto

```
droidcast/
├── main.py              ← Punto de entrada
├── app/
│   ├── theme.py         ← Paleta de colores y fuentes
│   ├── config.py        ← Configuración persistente (JSON)
│   ├── core/
│   │   ├── adb.py       ← Comandos ADB y validación
│   │   └── scrcpy.py    ← Descarga, actualización y ejecución
│   └── ui/
│       ├── dialogs.py   ← Diálogos modales reutilizables
│       ├── help_window.py ← Guía de uso
│       └── main_window.py ← Ventana principal
├── assets/              ← Icono y banner
├── tests/               ← Tests unitarios
└── docs/                ← Documentación
```

---

## Desarrollo

```bash
# Hot-reload (reinicia automáticamente al guardar cambios)
python dev.py

# Ejecutar tests
python -m pytest tests/test_tools.py -v

# Compilar ejecutable
pyinstaller DroidCast.spec
```

---

## Tecnologías

| Tecnología                                                      | Uso                           |
| --------------------------------------------------------------- | ----------------------------- |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Interfaz gráfica moderna      |
| [scrcpy](https://github.com/Genymobile/scrcpy)                  | Transmisión de pantalla       |
| [ADB](https://developer.android.com/tools/adb)                  | Comunicación con dispositivos |
| [Pillow](https://python-pillow.org/)                            | Procesamiento de imágenes     |
| [PyInstaller](https://pyinstaller.org/)                         | Empaquetado en .exe           |

---

## Contribuir

¡Las contribuciones son bienvenidas! Si quieres aportar:

1. Haz fork del proyecto
2. Crea una rama: `git checkout -b mi-mejora`
3. Haz commit: `git commit -m "Agrega nueva funcionalidad"`
4. Push: `git push origin mi-mejora`
5. Abre un Pull Request

Si encuentras un bug o tienes una sugerencia, abre un [Issue](https://github.com/soypercyabad/droidcast/issues).

---

## Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

<p align="center">
  Hecho con 💜 por <a href="https://github.com/soypercyabad">@soypercyabad</a>
</p>
