# 📱 Android Developer Tools — Guía de Uso

Herramienta para conectar tu celular Android a la PC, ver la pantalla en tiempo real e instalar aplicaciones (.apk) de forma remota.

---

## 📋 Requisitos Previos

1. **PC con Windows** (64-bit)
2. **Celular Android** con las opciones de desarrollador activadas
3. **Ambos dispositivos en la misma red Wi-Fi**

### ¿Cómo activar Opciones de Desarrollador?

1. Ve a **Ajustes → Acerca del teléfono**
2. Toca **"Número de compilación" 7 veces** hasta que aparezca "Ahora eres desarrollador"
3. Regresa a **Ajustes → Opciones de desarrollador**
4. Activa **"Depuración USB"**
5. _(Solo Xiaomi/Redmi/POCO)_: Activa también **"Depuración USB (Ajustes de seguridad)"**

> ⚠️ Si es la primera vez, conecta el celular por **cable USB**, abre la app, y acepta el mensaje de **"¿Permitir depuración USB?"** que aparece en el celular. Luego ya puedes usar Wi-Fi.

---

## 🚀 Uso Paso a Paso

### Paso 1: Abrir la Aplicación

Ejecuta `ToolsDeveloperAndroid.exe` (o `python ToolsDeveloperAndroid.py`).

La primera vez descargará automáticamente **scrcpy** (el motor de transmisión). Solo espera a que termine.

---

### Paso 2: Conectar el Dispositivo

1. En tu celular, ve a **Ajustes → Wi-Fi** y anota la **dirección IP** (ej: `192.168.1.100`)
2. En la app, escribe:
   - **IP Address**: La IP de tu celular
   - **Puerto**: `5555` (valor por defecto)
3. Presiona **"Conectar"** (botón azul)

✅ Si ve **"Dispositivo conectado"** en verde, ¡está listo!

❌ Si falla, verifica que:

- Ambos estén en la **misma red Wi-Fi**
- La **depuración USB** esté activada
- Hayas aceptado la autorización por USB al menos una vez

> El botón cambia a **"Desconectar"** (rojo) cuando está conectado. Presiónalo para terminar la conexión.

---

### Paso 3: Transmitir Pantalla

1. Con el dispositivo conectado, presiona **"▶ Trasmitir"** (botón morado)
2. Se abrirá una ventana con la pantalla de tu celular en tiempo real
3. Puedes interactuar con el celular usando el mouse

> 💡 Si la app detecta que tienes un **Xiaomi/Redmi/POCO**, te mostrará instrucciones adicionales para habilitar el control táctil.

---

### Paso 4: Instalar APK

1. En la columna derecha, presiona **📂** para seleccionar la carpeta donde están tus archivos `.apk`
2. Selecciona el archivo APK deseado del árbol de carpetas
3. Presiona **"Instalar APK"** (botón verde)
4. Espera a que termine la instalación

> Si el celular pide autorización en pantalla, acéptala desde el dispositivo.

---

## 🔄 Actualizaciones

La app verifica automáticamente si hay una versión nueva de scrcpy al transmitir. Si encuentra una actualización:

1. Te preguntará si deseas actualizar
2. Si aceptas, descarga la nueva versión
3. Elimina la versión anterior automáticamente
4. Reconecta tu dispositivo sin que tengas que hacer nada

---

## ❓ Solución de Problemas

| Problema                    | Solución                                                             |
| --------------------------- | -------------------------------------------------------------------- |
| "Sin dispositivo conectado" | Verifica IP, puerto y que estén en la misma red Wi-Fi                |
| No se puede instalar APK    | Activa "Instalar vía USB" en Opciones de desarrollador               |
| Sin control táctil (Xiaomi) | Activa "Depuración USB (Ajustes de seguridad)" y reinicia el celular |
| La conexión se pierde       | Verifica que el celular no entre en modo ahorro de energía           |
| scrcpy no inicia            | Asegúrate de tener un dispositivo conectado primero                  |

---

## 📌 Interfaz Rápida

```
┌──────────────────────────────────────────────────┐
│                 🔲 BANNER                        │
├────────────────────┬─────────────────────────────┤
│  DISPOSITIVO       │  INSTALAR APK               │
│  🔴 Desconectado   │  📂 Seleccionar carpeta     │
│  ▶ Trasmitir       │  📄 Lista de APKs           │
│                    │  [Instalar APK]              │
│  CONEXIÓN WI-FI    │                              │
│  IP: [___________] │                              │
│  Puerto: [____]    │                              │
│  [Conectar]        │                              │
└────────────────────┴─────────────────────────────┘
```

---

_Desarrollado por @soypercyabad_
