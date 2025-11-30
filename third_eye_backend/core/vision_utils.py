from __future__ import annotations

import base64
import logging
from typing import List, Optional, Dict, Any
import requests
import httpx
import json
from config.settings import settings

logger = logging.getLogger("third_eye_backend.vision")


def analyze_image(image_bytes: bytes) -> List[str]:
    """Analyze image bytes with Gemini Vision API and return object descriptions.

    Parameters
    ----------
    image_bytes: bytes
        Raw bytes of the image (e.g., JPEG/PNG) to analyze.

    Returns
    -------
    List[str]
        List containing the descriptive text from Gemini Vision API.
    """
    if not image_bytes:
        logger.warning("analyze_image called with empty image bytes")
        return ["No image provided"]

    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured")
        return ["API key not configured"]

    try:
        logger.info("Starting Gemini Vision API analysis")
        
        # Encode image to base64
        img_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Prepare the payload for Gemini API
        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": "Describe what you see in this image in one short sentence for navigation assistance. Focus on objects and their relative positions, like: 'A person is sitting in front of a desk with a laptop on it.'"
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "topK": 32,
                "topP": 1,
                "maxOutputTokens": 100
            }
        }

        # Prepare headers and parameters
        headers = {"Content-Type": "application/json"}
        params = {"key": settings.GEMINI_API_KEY}

        if settings.DEBUG_MODE:
            logger.info(f"Making request to Gemini API: {settings.GEMINI_API_URL}")
            logger.info(f"Payload size: {len(json.dumps(payload))} bytes")

        # Make the API request
        response = requests.post(
            settings.GEMINI_API_URL, 
            headers=headers, 
            params=params, 
            json=payload,
            timeout=30
        )

        if settings.DEBUG_MODE:
            logger.info(f"Gemini API response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"Gemini API request failed with status {response.status_code}: {response.text}")
            return ["API request failed"]

        # Parse the response
        result = response.json()
        
        if settings.DEBUG_MODE:
            logger.info(f"Gemini API response: {json.dumps(result, indent=2)}")

        # Extract the description from the response
        try:
            description = result["candidates"][0]["content"]["parts"][0]["text"]
            logger.info(f"Gemini detected: {description}")
            return [description]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.error(f"Response structure: {result}")
            return ["No clear objects detected"]

    except requests.exceptions.Timeout:
        logger.error("Gemini API request timed out")
        return ["API request timed out"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during Gemini API request: {e}")
        return ["Network error occurred"]
    except Exception as exc:
        logger.exception("Gemini Vision API analysis failed: %s", exc)
        return ["Analysis failed"]


def analyze_image_with_fallback(image_bytes: bytes) -> List[str]:
    """Analyze image with Gemini API and provide fallback response.
    
    Parameters
    ----------
    image_bytes: bytes
        Raw bytes of the image to analyze.
        
    Returns
    -------
    List[str]
        Description from Gemini API or fallback message.
    """
    result = analyze_image(image_bytes)
    
    # If we get an error response, provide a fallback
    if len(result) == 1 and any(error in result[0].lower() for error in [
        "api key not configured", "api request failed", "network error", 
        "analysis failed", "api request timed out"
    ]):
        return ["No object detected"]
    
    return result


def request_gemini_detections(image_bytes: bytes) -> Dict[str, Any]:
    """Request structured object detections (JSON only) from Gemini Vision."""
    if not image_bytes:
        raise ValueError("image_bytes cannot be empty.")
    if not settings.GEMINI_API_KEY:
        raise ValueError("Gemini API key is not configured.")

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    prompt = (
        "Identify every object in this image and respond ONLY with valid JSON using this schema:\n"
        '{"objects":[{"name":"<label>","bbox":[x1,y1,x2,y2],"confidence":0.0}]}\n'
        "Replace <label> and numeric values with the actual detections from this image. "
        "Do not repeat the example values, do not add narration, and output strictly valid JSON."
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": encoded,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
        },
    }

    timeout = httpx.Timeout(40.0, connect=10.0)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                settings.GEMINI_API_URL,
                params={"key": settings.GEMINI_API_KEY},
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover
        logger.error("Gemini API error: %s", exc.response.text)
        raise
    except httpx.HTTPError as exc:  # pragma: no cover
        logger.error("Gemini API network failure: %s", exc)
        raise

    logger.debug("Raw Gemini JSON: %s", response.text)
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("Gemini detection response was not a JSON object.")
    return body