from __future__ import annotations

from pydantic_settings import BaseSettings
import os
import os.path


class Settings(BaseSettings):
    # Server configuration
    PORT: int = 8000
    # YOLOv8 model path (can be changed to yolov8s.pt, yolov8m.pt, etc. for different sizes)
    YOLO_MODEL_PATH: str = "yolov8n.pt"

    class Config:
        env_file = ".env"


settings = Settings()


