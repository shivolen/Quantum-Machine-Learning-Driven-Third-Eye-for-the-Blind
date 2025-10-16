from __future__ import annotations

import time
from typing import Any, Dict

import cv2
import requests


URL = "http://127.0.0.1:8000/process_frame"


def main() -> None:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open webcam")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                break

            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                print("Failed to encode frame")
                break

            files = {"image": ("frame.jpg", buffer.tobytes(), "image/jpeg")}
            try:
                response = requests.post(URL, files=files, timeout=30)
                try:
                    data: Dict[str, Any] = response.json()
                except Exception:
                    data = {"status_code": response.status_code, "text": response.text}
                print(data)
            except Exception as exc:
                print(f"Request failed: {exc}")

            time.sleep(3)
            cv2.imshow("Third Eye Feed", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()


