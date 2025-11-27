from __future__ import annotations

import argparse
import base64
import binascii
import logging
from typing import Any, List

import asyncio

import httpx
from pathlib import Path

import sys
from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

PACKAGE_DIR = Path(__file__).resolve().parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from config.settings import settings
from core.tts_utils import speak
from core.vision_utils import analyze_image_with_fallback
from feature_utils import extract_features_from_gemini_response
from qml_inference import load_model_bundle, predict_risks
from tts_utils import speak_risk


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("third_eye_backend")


app = FastAPI(title="Third Eye for the Blind", version="1.0.0")

# CORS for any origin (for OpenCV / ESP32 testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    logger.info("Health check requested")
    return {"message": "API running successfully 🚀"}


@app.get("/test-mock")
async def test_mock() -> dict[str, Any]:
    """Test mock vision without image upload."""
    logger.info("Testing mock vision")
    try:
        from core.vision_utils import analyze_image_with_fallback
        # Test with empty bytes to trigger fallback mode
        objects = analyze_image_with_fallback(b"")
        return {"status": "success", "objects": objects}
    except Exception as exc:
        logger.exception("Mock test failed: %s", exc)
        return {"status": "error", "detail": str(exc), "objects": []}


class Base64ImagePayload(BaseModel):
    image: str


class PredictionPayload(BaseModel):
    image: str


async def _handle_image_bytes(image_bytes: bytes) -> JSONResponse:
    if not image_bytes:
        logger.warning("Empty image payload received")
        raise HTTPException(status_code=400, detail="Empty image payload")

    try:
        logger.info("Starting Vision analysis")
        objects: List[str] = await run_in_threadpool(analyze_image_with_fallback, image_bytes)
        logger.info("Vision analysis complete", extra={"num_objects": len(objects)})

        if len(objects) == 0:
            text = "No objects detected."
        else:
            text = objects[0] if len(objects) == 1 else ". ".join(objects)

        if settings.DEBUG_MODE:
            logger.info("TTS text: %s", text)

        logger.info("Starting TTS playback")
        await run_in_threadpool(speak, text)
        logger.info("TTS playback invoked")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "description": objects[0] if objects else "No objects detected",
                "objects": objects,
            },
        )
    except Exception as exc:
        logger.exception("Error while handling image bytes: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": f"Failed to process frame: {str(exc)}",
                "objects": [],
            },
        )


@app.post("/process_frame")
async def process_frame(image: UploadFile = File(...)) -> JSONResponse:
    """Accept an uploaded image, analyze with Gemini Vision API, generate TTS, return description."""
    logger.info("Image upload received", extra={"image_filename": image.filename, "content_type": image.content_type})

    try:
        allowed_types = {
            "image/jpeg",
            "image/jpg",
            "image/png",
        }
        if image.content_type not in allowed_types:
            logger.warning("Unsupported media type: %s", image.content_type)
            raise HTTPException(status_code=415, detail="Only JPEG and PNG images are supported")

        image_bytes = await image.read()
        return await _handle_image_bytes(image_bytes)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error in /process_frame: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": f"Failed to process frame: {str(exc)}",
                "objects": [],
            },
        )


@app.post("/detect_objects")
async def detect_objects(payload: Base64ImagePayload) -> JSONResponse:
    """Accept base64 JPEG payloads from the ESP32 snapshot client."""
    logger.info("Base64 image received for detection")
    try:
        image_bytes = base64.b64decode(payload.image, validate=True)
    except (binascii.Error, ValueError) as exc:
        logger.warning("Invalid base64 payload: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid base64-encoded image") from exc

    return await _handle_image_bytes(image_bytes)


async def _request_gemini_detections(image_bytes: bytes) -> dict[str, Any]:
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key is not configured.")

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Detect objects and provide JSON with a 'detections' array of "
                            "{name: string, bbox: {x1: float, y1: float, x2: float, y2: float}}. "
                            "Use normalized coordinates between 0 and 1."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": encoded,
                        }
                    },
                ]
            }
        ]
    }

    timeout = httpx.Timeout(40.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                settings.GEMINI_API_URL,
                params={"key": settings.GEMINI_API_KEY},
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Gemini API error: %s", exc.response.text)
            raise HTTPException(status_code=502, detail="Gemini API request failed.") from exc
        except httpx.HTTPError as exc:  # noqa: BLE001
            logger.error("Network error contacting Gemini API: %s", exc)
            raise HTTPException(status_code=502, detail="Gemini API network error.") from exc
    return response.json()


async def _predict_risk_from_frame(image_bytes: bytes) -> dict[str, Any]:
    gemini_response = await _request_gemini_detections(image_bytes)
    feature_vectors, object_names = extract_features_from_gemini_response(gemini_response)

    logger.info(
        "Gemini detections complete",
        extra={"objects": object_names, "count": len(object_names)},
    )

    if not feature_vectors:
        logger.info("No valid feature vectors found; defaulting to safe state.")
        message = await run_in_threadpool(speak_risk, 0)
        return {"risk": 0, "message": message, "objects_detected": []}

    risks = await run_in_threadpool(predict_risks, feature_vectors)
    logger.info("QML model returned predictions", extra={"predictions": risks})

    if not risks:
        logger.warning("Prediction returned no values; defaulting to safe state.")
        message = await run_in_threadpool(speak_risk, 0)
        return {"risk": 0, "message": message, "objects_detected": object_names}

    max_risk = int(max(risks))
    logger.info(
        "Highest risk computed",
        extra={"risk": max_risk, "objects_detected": object_names},
    )
    message = await run_in_threadpool(speak_risk, max_risk)
    logger.info("Risk message ready", extra={"message": message})

    return {
        "risk": max_risk,
        "message": message,
        "objects_detected": object_names,
    }


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Loading QML model into memory.")
    await asyncio.get_running_loop().run_in_executor(None, load_model_bundle)
    logger.info("QML model loaded.")


@app.post("/predict")
async def predict_endpoint(
    request: Request,
    image: UploadFile | None = File(default=None),
) -> JSONResponse:
    logger.info("Predict endpoint invoked.")
    image_bytes: bytes | None = None

    if image is not None:
        image_bytes = await image.read()
    else:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                payload_dict = await request.json()
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

            try:
                payload = PredictionPayload(**payload_dict)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=422, detail="JSON payload must include 'image'.") from exc

            if payload.image:
                try:
                    image_bytes = base64.b64decode(payload.image, validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise HTTPException(status_code=400, detail="Invalid base64 payload.") from exc
        elif content_type:
            form = await request.form()
            image_field = form.get("image")
            if isinstance(image_field, UploadFile):
                image_bytes = await image_field.read()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="No image data provided.")

    result = await _predict_risk_from_frame(image_bytes)
    return JSONResponse(status_code=200, content=result)


def run_server() -> None:
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)


def run_client_entrypoint() -> None:
    if settings.use_esp32:
        from client.client_camera_esp32 import run as run_esp32_client

        logger.info("USE_ESP32 enabled; starting ESP32 ingestion client")
        run_esp32_client()
    else:
        from client.client_camera import main as run_webcam_client

        logger.info("USE_ESP32 disabled; starting laptop webcam ingestion client")
        run_webcam_client()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Third Eye backend entrypoint")
    parser.add_argument(
        "--mode",
        choices=("server", "client"),
        default="server",
        help="server=run FastAPI (default), client=run ingestion loop",
    )
    args = parser.parse_args()

    if args.mode == "client":
        run_client_entrypoint()
    else:
        run_server()


