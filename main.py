from __future__ import annotations

import logging
from typing import List, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool

from config.settings import settings
from core.vision_utils import analyze_image
from core.tts_utils import speak


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
        from core.vision_utils import analyze_image
        # Test with empty bytes to trigger mock mode
        objects = analyze_image(b"")
        return {"status": "success", "objects": objects}
    except Exception as exc:
        logger.exception("Mock test failed: %s", exc)
        return {"status": "error", "detail": str(exc), "objects": []}


@app.post("/process_frame")
async def process_frame(image: UploadFile = File(...)) -> JSONResponse:
    """Accept an uploaded image, analyze with Vision API, generate TTS, return objects.

    Returns
    -------
    JSONResponse
        {"status": "success", "objects": ["Person", ...]}
    """
    logger.info("Image upload received", extra={"image_filename": image.filename, "content_type": image.content_type})

    try:
        # Validate content type (accept common image types)
        allowed_types = {
            "image/jpeg",
            "image/jpg",
            "image/png",
        }
        if image.content_type not in allowed_types:
            logger.warning("Unsupported media type: %s", image.content_type)
            raise HTTPException(status_code=415, detail="Only JPEG and PNG images are supported")

        image_bytes: bytes = await image.read()
        if not image_bytes:
            logger.warning("Empty image payload received")
            raise HTTPException(status_code=400, detail="Empty image payload")

        logger.info("Starting Vision analysis")
        objects: List[str] = await run_in_threadpool(analyze_image, image_bytes)
        logger.info("Vision analysis complete", extra={"num_objects": len(objects)})

        # Build TTS text
        text: str = (
            "No objects detected." if len(objects) == 0 else f"Detected: {', '.join(objects)}."
        )

        logger.info("Starting TTS playback")
        await run_in_threadpool(speak, text)
        logger.info("TTS playback invoked")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "objects": objects,
            },
        )

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - top-level exception guard for API route
        logger.exception("Error in /process_frame: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": f"Failed to process frame: {str(exc)}",
                "objects": []
            }
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)


