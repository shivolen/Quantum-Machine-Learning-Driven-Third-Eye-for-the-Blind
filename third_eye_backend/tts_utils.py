from __future__ import annotations

import logging

from core.tts_utils import speak

logger = logging.getLogger("third_eye_backend.risk_tts")

_RISK_MESSAGES = {
    2: "Danger ahead. Stop immediately.",
    1: "Be cautious ahead.",
    0: "Safe to move.",
}


def speak_risk(risk: int) -> str:
    message = _RISK_MESSAGES[2] if risk >= 2 else _RISK_MESSAGES.get(risk, _RISK_MESSAGES[0])
    try:
        speak(message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Risk TTS playback failed: %s", exc)
    return message

