"""PastroVoice Layer 3: Radio Dialogue Script Generator.

Uses Google Gemini (via google-genai) to transform structured rangeland advisory
data into conversational radio dialogue for pastoralist communities in Marsabit.
Includes an offline fallback mode for zero-cost local testing.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .payload import validate_payload, load_sample_payload

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"
SAMPLES_DIR = Path(__file__).parent / "samples"
SAMPLE_SCRIPT_FILE = SAMPLES_DIR / "sample_script.json"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_api_key(explicit_key: Optional[str] = None) -> str:
    """Resolve Gemini API key from parameter, os.environ, or .env file."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()

    # Read from .env if present
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                val = line.split("GEMINI_API_KEY=", 1)[1].strip()
                if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                    val = val[1:-1]
                if val:
                    os.environ["GEMINI_API_KEY"] = val
                    return val

    return ""


def _clean_json_response(raw_text: str) -> str:
    """Strip markdown code fence wrappers (```json ... ```) if present."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _load_offline_script(ward_name: str, lang: str = "sw") -> Dict[str, Any]:
    """Load pre-computed reference dialogue when Gemini API key is not configured."""
    with open(SAMPLE_SCRIPT_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    target_lang = "en" if lang.lower() in ("en", "english") else "sw"
    script = catalog.get(target_lang, catalog["sw"])
    script["ward"] = ward_name
    return script


def build_prompt(payload: Dict[str, Any], lang: str = "sw") -> str:
    """Format the appropriate language prompt template using payload data."""
    validated = validate_payload(payload)
    filename = "radio_en.txt" if lang.lower() in ("en", "english") else "radio_sw.txt"
    template_path = PROMPTS_DIR / filename

    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    template_text = template_path.read_text(encoding="utf-8")
    return template_text.format(**validated)


def generate_radio_script(
    payload: Dict[str, Any],
    lang: str = "sw",
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.5-flash-lite",
) -> Dict[str, Any]:
    """Generate a multi-turn radio dialogue script from an advisory payload.

    Calls Google Gemini live when an API key is available, else falls back to offline.
    """
    validated_payload = validate_payload(payload)
    resolved_key = _get_api_key(api_key)

    if not resolved_key:
        logger.info("No GEMINI_API_KEY found. Utilizing offline reference script for testing.")
        return _load_offline_script(validated_payload["ward_name"], lang=lang)

    # Call Google Gemini live via the new google-genai SDK
    try:
        from google import genai
        from google.genai import types

        logger.info("Calling Gemini live (%s) for %s...", model_name, validated_payload["ward_name"])
        client = genai.Client(api_key=resolved_key)
        prompt = build_prompt(validated_payload, lang=lang)

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        cleaned_text = _clean_json_response(response.text)
        data = json.loads(cleaned_text)
        logger.info("Gemini live script generation successful (%d turns).", len(data.get("dialogue", [])))
        return data

    except Exception as exc:
        logger.warning(
            "Gemini API call failed (%s: %s). Falling back to offline reference script.",
            type(exc).__name__,
            exc,
        )
        return _load_offline_script(validated_payload["ward_name"], lang=lang)
