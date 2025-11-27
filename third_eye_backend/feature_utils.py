from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple


logger = logging.getLogger("feature_utils")

FEATURE_VECTOR_LENGTH = 5

MOVING_KEYWORDS = {"car", "bike", "motorcycle", "bus", "scooter", "person", "runner", "running", "dog"}
STATIC_KEYWORDS = {"pole", "bench", "chair", "table", "wall", "door", "stairs", "railing", "sink", "tree", "pillar"}
BACKGROUND_KEYWORDS = {"window", "light", "poster", "sign", "floor", "sky"}


def compute_distance(bbox_height: float, image_height: float) -> float:
    if image_height <= 0:
        return 0.0
    distance = bbox_height / image_height
    return max(0.0, min(1.0, float(distance)))


def categorize_object(object_name: str) -> int:
    if not object_name:
        return 1
    label = object_name.lower().strip()
    if label in BACKGROUND_KEYWORDS:
        return 1
    if any(keyword in label for keyword in MOVING_KEYWORDS):
        return 3
    if any(keyword in label for keyword in STATIC_KEYWORDS):
        return 2
    return 1


def _parse_detections_from_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = response.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        for part in parts:
            text = part.get("text")
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                logger.debug("Unable to parse Gemini part as JSON.")
                continue
            if isinstance(payload, dict):
                detections = payload.get("detections") or payload.get("objects")
                if isinstance(detections, list):
                    return detections
            elif isinstance(payload, list):
                return payload
    logger.warning("Gemini response did not contain parsable detection data.")
    return []


def extract_features_from_gemini_response(response: Dict[str, Any]) -> Tuple[List[List[float]], List[str]]:
    detections = _parse_detections_from_response(response)
    features: List[List[float]] = []
    object_names: List[str] = []

    for detection in detections:
        name = detection.get("name") or detection.get("label")
        bbox = detection.get("bbox") or detection.get("bounding_box") or detection.get("box")
        if not name or not bbox:
            continue

        if isinstance(bbox, dict):
            y1 = float(bbox.get("y1", 0.0))
            y2 = float(bbox.get("y2", 0.0))
            image_height = float(bbox.get("image_height", 1.0)) or 1.0
        elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            y1 = float(bbox[1])
            y2 = float(bbox[3])
            image_height = 1.0
        else:
            continue

        bbox_height = abs(y2 - y1)
        distance = compute_distance(bbox_height, image_height)
        object_cat = categorize_object(name)

        feature_vector = [float(object_cat), float(distance), 0.0, 1.0, 0.0]
        if len(feature_vector) != FEATURE_VECTOR_LENGTH:
            logger.debug("Skipping malformed feature vector for %s", name)
            continue

        features.append(feature_vector)
        object_names.append(str(name))

    logger.info(
        "Extracted %s feature vectors from %s detections",
        len(features),
        len(detections),
    )
    if features:
        logger.debug("Feature vectors: %s", features)

    return features, object_names

