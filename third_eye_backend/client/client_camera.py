from __future__ import annotations

import time
from typing import Any, Dict

import cv2
import requests


URL = "http://127.0.0.1:8000/process_frame"
FRAME_INTERVAL = 3.0  # seconds between frame captures


def main() -> None:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open webcam")
        return

    print(f"Starting Third Eye camera feed (capturing every {FRAME_INTERVAL}s)")
    print("Press 'q' to quit")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                break

            # Show the live feed
            cv2.imshow("Third Eye Feed", frame)
            
            # Check for quit key
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            # Encode frame for API
            success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success:
                print("Failed to encode frame")
                continue

            # Send frame to API
            files = {"image": ("frame.jpg", buffer.tobytes(), "image/jpeg")}
            try:
                print("Sending frame to Gemini API...")
                response = requests.post(URL, files=files, timeout=30)
                
                if response.status_code == 200:
                    try:
                        data: Dict[str, Any] = response.json()
                        if "description" in data:
                            print(f"🎯 Gemini says: {data['description']}")
                        else:
                            print(f"📊 Response: {data}")
                    except Exception as e:
                        print(f"Failed to parse JSON response: {e}")
                        print(f"Raw response: {response.text}")
                else:
                    print(f"API request failed with status {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                print("⚠️  Request timed out - API may be slow")
            except requests.exceptions.ConnectionError:
                print("❌ Connection failed - is the server running?")
            except Exception as exc:
                print(f"❌ Request failed: {exc}")

            # Wait before next capture
            time.sleep(FRAME_INTERVAL)
            
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera feed stopped")


if __name__ == "__main__":
    main()


