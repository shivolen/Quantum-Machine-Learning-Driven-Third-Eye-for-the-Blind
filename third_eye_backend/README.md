## Third Eye for the Blind — FastAPI Backend

An end-to-end assistive vision stack that now ingests frames directly from an ESP32-CAM (AI Thinker) running the Arduino `CameraWebServer` firmware.

### 🧠 System Overview
- **Capture:** ESP32-CAM snapshot endpoint `http://192.168.1.9/capture`
- **Transport:** Python ingestion client posts Base64 JPEGs to `POST /detect_objects`
- **Intelligence:** FastAPI backend calls Gemini Vision (with local fallback) to describe scenes
- **Audio:** gTTS + speaker playback announce the description in real time

### 🔌 Hardware & Network
- ESP32-CAM (AI Thinker) + ESP32-CAM MB programmer
- Connected over Wi-Fi SSID `Airtel_mela_8808`
- Static IP: `192.168.1.9`
- Working firmware: Arduino `CameraWebServer`
- Useful endpoints:
  - UI: `http://192.168.1.9/`
  - Live MJPEG: `http://192.168.1.9/stream`
  - **Snapshot (used):** `http://192.168.1.9/capture`
  - Flash: `http://192.168.1.9/flash`
  - Controls: `http://192.168.1.9/control?var=PARAM&val=VALUE`

Snapshots are preferred over the MJPEG stream because each request returns a clean JPEG, avoids dealing with streaming boundaries, and keeps retries simple when Wi-Fi drops.

### ⚙️ Setup
1. `cd third_eye_backend`
2. Create/activate a Python 3.10+ virtual environment.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the sample environment file and adjust if needed:
   ```bash
   cp .env.example .env
   ```

### 🌐 Environment Variables
```
PORT=8000
ESP32_IP=192.168.1.9
BACKEND_ENDPOINT=http://127.0.0.1:8000/detect_objects
SEND_INTERVAL=3
USE_ESP32=1
```
- `ESP32_IP` — camera IP (no protocol needed).
- `BACKEND_ENDPOINT` — FastAPI route that accepts `{ "image": "<base64_jpeg>" }`.
- `SEND_INTERVAL` — seconds between snapshots (float accepted).
- `USE_ESP32` — toggle for choosing ESP32 client vs. laptop webcam client.

### 🚀 Running the Platform
**Start the FastAPI backend:**
```bash
uvicorn main:app --reload
```

**Run the ESP32 ingestion client (automatically loads `.env`):**
```bash
python client/client_camera_esp32.py
```
Or use the main runner toggle:
```bash
USE_ESP32=1 python main.py --mode client
```
Setting `USE_ESP32=0` falls back to the existing webcam OpenCV client without touching code.

### 🔁 Snapshot vs Stream
- **Snapshot (`/capture`):** Stateless, every request is atomic; easier to recover from Wi-Fi hiccups, and perfect for spacing frames every few seconds.
- **Stream (`/stream`):** Continuous MJPEG feed best for high FPS use-cases, but requires parsing multipart frames and reconnect logic.
Given the reliability requirement, the ingestion client always uses `/capture`.

### 📦 Project Structure
```
third_eye_backend/
├── main.py                   # FastAPI app + client toggle runner
├── client/
│   ├── client_camera.py      # Existing laptop webcam ingestion
│   └── client_camera_esp32.py# New ESP32 snapshot ingestion
├── core/
│   ├── tts_utils.py
│   └── vision_utils.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── README.md
├── requirements.txt
└── .env / .env.example
```

### 🔊 Full Pipeline
1. ESP32-CAM captures a JPEG via `/capture`.
2. `client_camera_esp32.py` encodes it as Base64 and posts to `POST /detect_objects`.
3. FastAPI validates input and forwards bytes to Gemini Vision with fallback logic.
4. Vision description is converted to speech through gTTS.
5. Audio plays locally, completing the ESP32 → FastAPI → Gemini → TTS → Output loop.

### 🧪 Diagnostics
- Health check: `curl http://127.0.0.1:8000/`
- Mock endpoint: `curl http://127.0.0.1:8000/test-mock`
- Logs: the ESP32 client produces structured logs for snapshot retrieval, retries, and API responses.

### 📄 License
For demonstration and educational use.

