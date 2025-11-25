from __future__ import annotations

import argparse
import base64
import binascii
import logging
from typing import Any, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config.settings import settings
from core.tts_utils import speak
from core.vision_utils import analyze_image_with_fallback


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


