# Gemini API Setup Instructions

## 1. Get Your Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key" and create a new API key
4. Copy the API key

## 2. Configure Your Environment

Create a `.env` file in the `third_eye_backend` directory with:

```env
GEMINI_API_KEY=your_actual_api_key_here
PORT=8000
FRAME_CAPTURE_INTERVAL=1.0
DEBUG_MODE=false
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the Server

```bash
python main.py
```

## 5. Run the Client

In a separate terminal:

```bash
python client/client_camera.py
```

## Features

- **Real-time Vision**: Captures frames every 1 second (configurable)
- **Gemini Integration**: Uses Google's Gemini Pro Vision for object detection
- **Natural Language**: Returns human-readable descriptions instead of bounding boxes
- **TTS Integration**: Speaks the descriptions aloud
- **Debug Mode**: Set `DEBUG_MODE=true` in `.env` for detailed logging

## Example Output

Instead of: `["person", "chair", "laptop"]`

You get: `"A person is sitting at a desk with a laptop open in front of them"`

## Troubleshooting

- Make sure your API key is correctly set in the `.env` file
- Check that the server is running on port 8000
- Enable debug mode to see detailed API responses
- Ensure your webcam is working and not being used by other applications
