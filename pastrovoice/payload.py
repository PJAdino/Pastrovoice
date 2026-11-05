"""PastroVoice Layer 3: Advisory Payload Validator and Fixture Loader.

Ensures incoming data from Layer 2 conforms to the required structure
before sending it to Gemini for script generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

SAMPLE_PAYLOAD_FILE = Path(__file__).parent / "samples" / "sample_payload.json"

REQUIRED_FIELDS = [
    "ward_name",
    "county",
    "weather_outlook",
    "pasture_status",
    "critical_water_point_dry",
    "safe_water_point_available",
    "market_advice",
    "veterinary_action",
]


class InvalidPayloadError(ValueError):
    """Raised when an advisory payload is missing critical fields."""
    pass


def validate_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that the advisory payload has all required fields.

    Args:
        data: Dictionary of ward advisory data.

    Returns:
        The validated dictionary.

    Raises:
        InvalidPayloadError: If required fields are missing or empty.
    """
    if not isinstance(data, dict):
        raise InvalidPayloadError(f"Payload must be a dictionary, got {type(data).__name__}")

    missing = []
    for field in REQUIRED_FIELDS:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)

    if missing:
        raise InvalidPayloadError(
            f"Advisory payload is missing required field(s): {', '.join(missing)}"
        )

    return data


def load_sample_payload(lang: str = "sw") -> Dict[str, Any]:
    """Load the reference offline sample payload for Marsabit County (Laisamis).

    Args:
        lang: Target language ('sw' for Kiswahili, 'en' for English).

    Returns:
        A validated payload dictionary.
    """
    with open(SAMPLE_PAYLOAD_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if lang == "en":
        payload = {
            "ward_name": raw["ward_name"],
            "county": raw["county"],
            "language": "en",
            "urgency_level": raw["urgency_level"],
            "weather_outlook": raw.get("weather_outlook_en", raw["weather_outlook"]),
            "pasture_status": raw.get("pasture_status_en", raw["pasture_status"]),
            "critical_water_point_dry": raw.get("critical_water_point_dry_en", raw["critical_water_point_dry"]),
            "safe_water_point_available": raw.get("safe_water_point_available_en", raw["safe_water_point_available"]),
            "market_advice": raw.get("market_advice_en", raw["market_advice"]),
            "veterinary_action": raw.get("veterinary_action_en", raw["veterinary_action"]),
        }
    else:
        payload = {
            "ward_name": raw["ward_name"],
            "county": raw["county"],
            "language": "sw",
            "urgency_level": raw["urgency_level"],
            "weather_outlook": raw["weather_outlook"],
            "pasture_status": raw["pasture_status"],
            "critical_water_point_dry": raw["critical_water_point_dry"],
            "safe_water_point_available": raw["safe_water_point_available"],
            "market_advice": raw["market_advice"],
            "veterinary_action": raw["veterinary_action"],
        }

    return validate_payload(payload)
