from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

from gtts import gTTS
from playsound import playsound

logger = logging.getLogger("third_eye_backend.tts")


def speak(text: str, *, lang: str = "en", output_path: Optional[str] = None) -> None:
    """Convert text to speech and play it.

    Parameters
    ----------
    text: str
        Text to synthesize and play.
    lang: str, optional
        Language code for gTTS (default: "en").
    output_path: Optional[str]
        If provided, save audio to this path; otherwise use a temporary mp3.
    """
    to_say = text.strip() if text and text.strip() else "No objects detected."

    try:
        tts = gTTS(text=to_say, lang=lang)

        cleanup_needed = False
        file_path = output_path
        if not file_path:
            fd, tmp_path = tempfile.mkstemp(suffix=".mp3", prefix="third_eye_")
            os.close(fd)
            file_path = tmp_path
            cleanup_needed = True

        tts.save(file_path)
        logger.info("Saved TTS audio", extra={"file": file_path})

        try:
            # Use blocking=False for better Windows compatibility
            playsound(file_path, block=True)
            logger.info("Audio playback completed")
        except Exception as play_exc:  # noqa: BLE001
            logger.exception("Audio playback failed: %s", play_exc)
            # Fallback: just log the text if audio fails
            logger.info("TTS Text (audio failed): %s", to_say)
        finally:
            if cleanup_needed:
                try:
                    os.remove(file_path)
                except OSError:
                    # Not critical if temp cleanup fails
                    pass

    except Exception as exc:  # noqa: BLE001
        logger.exception("TTS synthesis failed: %s", exc)


