## Third Eye for the Blind — FastAPI Backend

An AI vision assistant backend that detects objects from camera frames using local YOLOv8 inference and speaks results via TTS, designed for visually impaired users.

### 🧠 Overview
- **Input**: Live frames sent via API (multipart/form-data)
- **Processing**: Local YOLOv8 object detection (no cloud APIs required)
- **Output**: Text-to-Speech playback with gTTS and structured JSON response
- **Client**: OpenCV-based test client for real-time testing

### ⚙️ Setup Instructions
1) Clone or copy the `third_eye_backend` folder.
2) Create and activate a Python 3.10+ virtual environment.
3) Install requirements:
```bash
pip install -r requirements.txt
```
4) No API keys required! The system uses local YOLOv8 inference.
5) Optional: Create `.env` file to customize settings:
```env
PORT=8000
YOLO_MODEL_PATH=yolov8n.pt
```

#### YOLO Model Options
- `yolov8n.pt` - Nano (fastest, least accurate)
- `yolov8s.pt` - Small (balanced)
- `yolov8m.pt` - Medium (more accurate)
- `yolov8l.pt` - Large (most accurate, slower)

The model will be automatically downloaded on first run.

### ▶️ Run the backend
```bash
uvicorn main:app --reload
```
Server will start at `http://127.0.0.1:8000` by default.

### ✅ Health check
```bash
curl http://127.0.0.1:8000/
```
Response:
```json
{"message": "API running successfully 🚀"}
```

### 📸 Test with sample image (Python)
```python
import requests

files = {"image": open("test.jpg", "rb")}
res = requests.post("http://127.0.0.1:8000/process_frame", files=files)
print(res.json())
```

### 🎥 Real-time test client
Run the OpenCV client to stream frames every 3 seconds:
```bash
python client/client_camera.py
```
Press `q` in the preview window to quit.

### 🗂️ Project Structure
```
third_eye_backend/
├── main.py
├── core/
│   ├── vision_utils.py
│   └── tts_utils.py
├── config/
│   ├── settings.py
│   └── __init__.py
├── client/
│   └── client_camera.py
├── requirements.txt
├── .env  # not committed; see example in README
└── README.md
```

### 🔧 Implementation Notes
- All endpoints are async. CPU/IO-heavy calls (Vision, gTTS/playsound) run in a threadpool.
- CORS is open to all origins for ease of testing with OpenCV or embedded devices.
- Structured logging is enabled across the app.

### 🚨 Error Handling
- Empty images or unexpected errors return proper HTTP codes and JSON messages.
- YOLOv8/TTS errors are logged; the API responds gracefully.
- Model loading failures are handled gracefully with fallback responses.

### ☁️ Deployment (Render/Railway)
- No API keys required for deployment!
- Start command:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```
- For Render/Railway: configure a Web Service and set `PORT` only.
- The YOLOv8 model will be downloaded automatically on first startup.

### 📄 License
For demonstration/educational use.


