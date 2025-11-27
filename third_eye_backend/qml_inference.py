from __future__ import annotations

import sys
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
import logging

import joblib
import numpy as np
from feature_utils import FEATURE_VECTOR_LENGTH

BASE_DIR = Path(__file__).resolve().parents[1]
MODELS_PATH = BASE_DIR / "models" / "quantum" / "qml_model.pkl"

if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from scripts.train_quantum import predict as qml_predict  # noqa: E402

logger = logging.getLogger("third_eye_backend.qml")

_MODEL_BUNDLE: Optional[Dict[str, Any]] = None
_MODEL_LOCK = Lock()


def load_model_bundle(force: bool = False) -> Dict[str, Any]:
    global _MODEL_BUNDLE

    if _MODEL_BUNDLE is not None and not force:
        return _MODEL_BUNDLE

    with _MODEL_LOCK:
        if _MODEL_BUNDLE is None or force:
            if not MODELS_PATH.exists():
                raise FileNotFoundError(f"QML model not found at {MODELS_PATH}")
            _MODEL_BUNDLE = joblib.load(MODELS_PATH)
            logger.info("Loaded QML model bundle from %s", MODELS_PATH)
    return _MODEL_BUNDLE


def predict_risks(feature_vectors: List[List[float]]) -> List[int]:
    if not feature_vectors:
        return []

    matrix = np.asarray(feature_vectors, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != FEATURE_VECTOR_LENGTH:
        raise ValueError(
            f"feature_vectors must be a 2D array with shape (n, {FEATURE_VECTOR_LENGTH})."
        )

    logger.info("Predicting risk for %s feature vector(s)", matrix.shape[0])
    logger.debug("Feature matrix: %s", matrix.tolist())

    bundle = load_model_bundle()
    predictions = qml_predict(matrix, model_bundle=bundle)
    if predictions is None or len(predictions) == 0:
        raise ValueError("Prediction failed to return any values.")

    result = [int(value) for value in predictions]
    logger.info("Model risk predictions: %s", result)
    return result


def predict_risk(feature_vector: list[float]) -> int:
    predictions = predict_risks([feature_vector])
    if not predictions:
        raise ValueError("Prediction failed to produce a result.")
    return predictions[0]

