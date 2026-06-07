# Crowdless 🚫👥

**Crowdless** es un sistema inteligente e integrado de control de afluencia, reserva de visitas y validación de identidad para museos. Combina una plataforma web en React para los visitantes, un backend en FastAPI con modelos de Machine Learning (XGBoost) para la predicción de asistencia, y un sistema de hardware basado en microcontroladores ESP32 con pantalla TFT y cámara para la validación automatizada de entradas y documentos de identidad.

---

## 📌 Arquitectura del Proyecto

El repositorio está dividido en tres componentes principales:

1. **`frontend/`**: Aplicación web desarrollada con **React + Vite** y **React Router**. Permite a los usuarios seleccionar la fecha y hora de su visita, realizar el pago simulado de las entradas, registrar los datos de los visitantes y descargar sus tiquetes con códigos QR.
2. **`backend/`**: Servidor API construido en **FastAPI** y respaldado por **Firebase Firestore** como base de datos.
   - Gestiona el inventario de franjas horarias y reservas.
   - Cuenta con un módulo de predicción de afluencia basado en un modelo **XGBoost** entrenado para predecir la afluencia futura a partir de variables como el día de la semana, mes, festivos colombianos e historial reciente.
   - Expone endpoints para la validación transaccional de códigos QR y la verificación de cédulas de ciudadanía colombianas a través de la API de **Roboflow** y OCR.
3. **`firmware/`**: Firmware basado en **PlatformIO** y **Arduino** para dos microcontroladores:
   - **`esp32_tft/`**: Microcontrolador central (ESP32 DevKit V1) conectado a una pantalla ILI9341 con panel táctil capacitivo/resistivo. Utiliza la librería **LVGL** para renderizar una interfaz gráfica interactiva y realiza solicitudes HTTP al backend para autorizar accesos.
   - **`esp32cam_scanner/`**: Módulo esclavo (ESP32-CAM AI-Thinker) que realiza la lectura física de los códigos QR de los tiquetes y captura imágenes en resolución VGA de los documentos de identidad para enviarlos serialmente al microcontrolador central.

---

## 🛠️ Requisitos Previos

Antes de ejecutar los componentes, asegúrate de tener instalado:
* **Node.js** (Versión 18 o superior)
* **Python** (Versión 3.10 o superior)
* **PlatformIO** (Extensión en VS Code o CLI) para compilar y cargar el firmware.
* Cuenta y proyecto en **Google Cloud/Firebase** con Firestore habilitado.
* Claves API para servicios externos (**Roboflow** y **SendGrid**).

---

## 🚀 Instrucciones de Configuración y Ejecución

### 1. Servidor Backend (`/backend`)

El backend expone la lógica de negocio, bases de datos y machine learning.

1. **Configurar el entorno virtual de Python**:
   ```bash
   cd backend
   python -m venv .venv
   # En Windows:
   .venv\Scripts\activate
   # En macOS/Linux:
   source .venv/bin/activate
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**:
   Copia el archivo de ejemplo y edita sus valores:
   ```bash
   cp .env.example .env
   ```
   Asegúrate de llenar las siguientes variables clave en el archivo `.env`:
   - `FIRESTORE_PROJECT_ID`: El ID de tu proyecto de Firebase.
   - `GOOGLE_APPLICATION_CREDENTIALS`: Ruta absoluta al archivo JSON de credenciales de la cuenta de servicio de Firebase.
   - `ROBOFLOW_API_URL` y `ROBOFLOW_API_KEY`: Para la validación visual de la cédula.
   - `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `SENDGRID_FROM_NAME`: Para el envío automatizado de tiquetes por correo electrónico.
   - `QR_SIGNING_SECRET`: Clave secreta para firmar/validar los códigos QR de forma segura.

4. **Ejecutar el servidor en desarrollo**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   La documentación interactiva de la API estará disponible en `http://127.0.0.1:8000/docs`.

---

### 2. Aplicación Web Frontend (`/frontend`)

El frontend permite a los usuarios reservar y comprar entradas.

1. **Instalar dependencias de Node.js**:
   ```bash
   cd ../frontend
   npm install
   ```

2. **Configurar variables de entorno**:
   Copia el archivo de ejemplo y ajusta la URL base de la API de backend:
   ```bash
   cp .env.example .env
   ```
   Define el endpoint del backend en tu archivo `.env`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```

3. **Ejecutar en modo desarrollo**:
   ```bash
   npm run dev
   ```
   La aplicación se abrirá en `http://localhost:5173`.

4. **Compilar para producción** (Opcional):
   ```bash
   npm run build
   npm run preview
   ```

---

### 3. Dispositivos de Hardware (`/firmware`)

Ambos firmwares están configurados como proyectos de **PlatformIO**.

#### Conexión Física (Wiring) entre ESP32 Central y ESP32-CAM:
* **ESP32 Central (TX2, Pin 17)** ➡️ **ESP32-CAM (RX, Pin 3)**
* **ESP32 Central (RX2, Pin 16)** ➡️ **ESP32-CAM (TX, Pin 1)**
* **GND** ➡️ **GND** (Común entre ambos dispositivos)
* *Nota: Asegúrate de alimentar correctamente el módulo ESP32-CAM (preferiblemente con una fuente externa de 5V dado el alto consumo de corriente al usar la cámara y el flash).*

#### Cargar Firmware en ESP32-CAM (`/firmware/esp32cam_scanner`):
1. Abre el directorio `/firmware/esp32cam_scanner` en VS Code con PlatformIO.
2. Si es necesario, edita el puerto de carga (`upload_port`) en `platformio.ini`.
3. Haz clic en **Build** y luego en **Upload** para grabar el código en la tarjeta ESP32-CAM.

#### Cargar Firmware en ESP32 Central (`/firmware/esp32_tft`):
1. Abre el directorio `/firmware/esp32_tft` en VS Code con PlatformIO.
2. Abre el archivo `firmware/esp32_tft/src/main.cpp` y configura tus credenciales Wi-Fi locales y la URL de tu backend:
   ```cpp
   #define WIFI_SSID "Tu_Nombre_De_Red"
   #define WIFI_PASSWORD "Tu_Contraseña_De_Red"
   #define BACKEND_BASE_URL "http://<IP_DE_TU_BACKEND>:8000/api/v1"
   ```
3. Realiza la compilación (**Build**) y carga del firmware (**Upload**) mediante PlatformIO. El microcontrolador central iniciará la UI en la pantalla TFT y establecerá conexión con el backend y la cámara esclava.

---

## 🔒 Flujo de Validación e Identidad

1. El visitante presenta su tiquete impreso o en el móvil.
2. El operario o guarda utiliza la pantalla táctil para iniciar la lectura.
3. El ESP32 Central envía la instrucción `CAPTURE_QR` al ESP32-CAM.
4. El ESP32-CAM escanea el código QR, extrae su contenido y lo envía de vuelta por serial UART.
5. El ESP32 Central consulta el backend (`/validation/qr`) para certificar que el QR no haya caducado, corresponda a la fecha y hora actuales, y que su pago esté aprobado.
6. Si el tiquete requiere verificación de identidad (e.g., control de tipo de entrada o seguridad), el ESP32 Central ordena `CAPTURE_DOC`.
7. El ESP32-CAM captura una foto de la cédula y la transmite en fragmentos al ESP32 Central.
8. El ESP32 Central la remite al backend (`/validation/id-card`), donde se realiza detección de documento vía Roboflow y OCR para contrastar el nombre y número de documento contra los datos de la reserva en Firestore.
9. Si todas las validaciones son correctas, el backend registra el tiquete como validado transaccionalmente y se le concede acceso al visitante mediante una confirmación visual en la pantalla TFT.