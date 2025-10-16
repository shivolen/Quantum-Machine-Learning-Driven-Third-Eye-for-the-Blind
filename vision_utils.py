from __future__ import annotations

import logging
from typing import List
import cv2
import numpy as np
from ultralytics import YOLO
from config.settings import settings

logger = logging.getLogger("third_eye_backend.vision")

# Load YOLOv8 model once at module level for efficiency
try:
    model = YOLO(settings.YOLO_MODEL_PATH)
    logger.info(f"YOLOv8 model loaded successfully: {settings.YOLO_MODEL_PATH}")
except Exception as e:
    logger.error(f"Failed to load YOLOv8 model: {e}")
    model = None


def analyze_image(image_bytes: bytes) -> List[str]:
    """Analyze image bytes with YOLOv8 model and return object names.

    Parameters
    ----------
    image_bytes: bytes
        Raw bytes of the image (e.g., JPEG/PNG) to analyze.

    Returns
    -------
    List[str]
        List of detected object names (capitalized, unique in input order).
    """
    if not image_bytes:
        logger.warning("analyze_image called with empty image bytes")
        return []

    if model is None:
        logger.error("YOLOv8 model not loaded")
        return []

    try:
        logger.info("Starting YOLOv8 inference")
        
        # Convert image bytes to OpenCV format
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            logger.error("Failed to decode image bytes")
            return []

        # Run YOLOv8 inference
        results = model(frame)
        logger.info(f"YOLOv8 inference completed, got {len(results)} results")
        
        # Extract detected object names
        detected_objects = []
        seen = set()
        total_detections = 0
        
        for result in results:
            if result.boxes is not None:
                total_detections += len(result.boxes)
                logger.info(f"Found {len(result.boxes)} detections in this result")
                for box in result.boxes:
                    # Get class ID and confidence
                    cls_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = model.names[cls_id]
                    
                    logger.info(f"Detection: {class_name} (confidence: {confidence:.3f})")
                    
                    # Only include high-confidence detections (lowered threshold for better detection)
                    if confidence > 0.25:
                        # Capitalize first letter
                        cap_name = class_name[0].upper() + class_name[1:] if class_name else class_name
                        
                        if cap_name and cap_name not in seen:
                            detected_objects.append(cap_name)
                            seen.add(cap_name)
                            logger.info(f"Added to results: {cap_name}")
            else:
                logger.info("No boxes found in this result")
        
        logger.info(f"Total detections: {total_detections}, Final objects: {detected_objects}")
        
        logger.info(f"YOLOv8 detected {len(detected_objects)} objects: {detected_objects}")
        
        # Fallback response if no objects detected
        if not detected_objects:
            logger.info("No objects detected with confidence > 0.5")
            return ["No objects detected"]
        
        return detected_objects

    except Exception as exc:
        logger.exception("YOLOv8 vision analysis failed: %s", exc)
        return []


