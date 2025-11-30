from __future__ import annotations

import logging
from typing import List

from core.tts_utils import speak

logger = logging.getLogger("third_eye_backend.risk_tts")

_RISK_MESSAGES = {
    2: "Danger ahead. Stop immediately.",
    1: "Be cautious ahead.",
    0: "Safe to move.",
}


def speak_risk(risk: int, *, announce: bool = True) -> str:
    message = _RISK_MESSAGES[2] if risk >= 2 else _RISK_MESSAGES.get(risk, _RISK_MESSAGES[0])
    if announce:
        try:
            speak(message)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Risk TTS playback failed: %s", exc)
    return message


def build_spoken_sentence(object_names: List[str], risk: int) -> str:
    safe_names = [name for name in object_names if isinstance(name, str) and name.strip()]
    if not safe_names:
        prefix = "No obstacles detected."
    elif len(safe_names) == 1:
        prefix = f"{safe_names[0]} ahead."
    else:
        prefix = f"{', '.join(safe_names)} ahead."

    risk_message = speak_risk(risk, announce=False)
    return f"{prefix} {risk_message}".strip()


TRIVIAL_OBJECTS = {
    "window",
    "floor",
    "light",
    "sky",
    "wall",
    "ceiling",
    "bag",
    "shoe",
    "helmet",
    "cap",
}

VEHICLES = {"car", "bus", "truck", "scooter", "bike", "motorcycle", "bicycle"}
FURNITURE = {"desk", "chair", "bench", "table"}
NAVIGATION = {"staircase", "stairs", "elevator", "door", "railing", "pole", "corridor", "hallway"}
PEOPLE = {"person", "man", "woman", "child", "boy", "girl", "human"}
OBSTACLES = {"pole", "pillar", "tree", "bin", "box"}


def summarize_objects_to_sentence(object_names: List[str]) -> str:
    cleaned: List[str] = []
    for name in object_names:
        if not name:
            continue
        label = name.strip().lower()
        if not label or label in TRIVIAL_OBJECTS:
            continue
        cleaned.append(label)

    if not cleaned:
        return "Path is clear"

    if any(label in {"staircase", "stairs"} for label in cleaned):
        return "Staircase ahead"
    if "elevator" in cleaned:
        return "Elevator ahead"

    vehicle = next((label for label in cleaned if label in VEHICLES), None)
    if vehicle:
        return f"{vehicle.capitalize()} ahead"

    people_count = sum(1 for label in cleaned if label in PEOPLE)
    if people_count > 2:
        return "Crowd ahead"
    if people_count == 1:
        return "Person ahead"

    if any(label in FURNITURE for label in cleaned):
        return "Desk and chairs ahead"

    if "door" in cleaned:
        return "Door ahead"
    if any(label in {"corridor", "hallway"} for label in cleaned):
        return "Hallway ahead"

    if any(label in OBSTACLES for label in cleaned):
        return "Obstacle ahead"

    primary = cleaned[0]
    return f"{primary.capitalize()} ahead"

