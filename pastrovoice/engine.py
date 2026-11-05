"""PastroVoice Layer 3 Master Engine & CLI Entrypoint.

Orchestrates the full Layer 3 pipeline:
[Layer 2 Cloud DB / Payload] -> [Gemini Radio Dialogue JSON] -> [Radio Spoken MP3 Audio]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .payload import validate_payload
from .bridge import build_advisory_payload_from_db
from .script_generator import generate_radio_script
from .audio_synthesizer import synthesize_radio_broadcast

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pastrovoice")


def run_pastrovoice(
    ward: str = "Laisamis",
    lang: str = "sw",
    custom_payload: Optional[Dict[str, Any]] = None,
    output_dir: str | Path = "output",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the end-to-end Layer 3 pipeline for a specific rangeland ward.

    Args:
        ward: Ward name (e.g. 'Laisamis', 'North Horr', 'Marsabit Central').
        lang: Target language ('sw' for Kiswahili, 'en' for English).
        custom_payload: Optional dict of raw ward indicators. If None, queries Layer 2 database.
        output_dir: Directory where the script JSON and MP3 audio will be saved.
        api_key: Optional Google Gemini API key.

    Returns:
        Dict containing:
        {
            "ward": str,
            "language": str,
            "script": dict,
            "script_file": str,
            "audio_file": str,
            "file_size_kb": float,
        }
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lang_code = "sw" if lang.lower() in ("sw", "kiswahili", "swahili") else "en"

    print("\n" + "=" * 56)
    print(f">> PASTROVOICE LAYER 3: MULTIMODAL AUDIO ENGINE")
    print(f"   Target Ward: {ward} | Language: {'Kiswahili' if lang_code == 'sw' else 'English'}")
    print("=" * 56 + "\n")

    # [1/3] Prepare and Validate Advisory Payload from Layer 2
    print(f"[1/3] Fetching and mapping Layer 2 advisory data for {ward}...")
    if custom_payload:
        payload = validate_payload(custom_payload)
    else:
        payload = build_advisory_payload_from_db(ward_name=ward, lang=lang_code)

    print(f"      + Weather: {payload['weather_outlook']}")
    print(f"      + Pasture: {payload['pasture_status']}")
    print(f"      + Dry Point: {payload['critical_water_point_dry']}")
    print(f"      + Safe Point: {payload['safe_water_point_available']}")

    # [2/3] Generate Multi-Turn Radio Dialogue Script
    print(f"\n[2/3] Synthesizing conversational dialogue script...")
    script_data = generate_radio_script(
        payload=payload,
        lang=lang_code,
        api_key=api_key,
    )
    total_turns = len(script_data.get("dialogue", []))
    print(f"      + Script ready: {total_turns} alternating dialogue turns.")

    # Save script JSON alongside audio for radio studio cue sheets
    clean_ward = ward.replace(" ", "_")
    script_file = out_dir / f"{clean_ward}_{lang_code}_script.json"
    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    print(f"      + Cue-sheet saved: {script_file}")

    # [3/3] Synthesize Broadcast Audio via TTS
    print(f"\n[3/3] Synthesizing speech audio and assembling master MP3...")
    audio_res = synthesize_radio_broadcast(
        script_data=script_data,
        output_dir=out_dir,
        filename=f"{clean_ward}_{lang_code}_advisory.mp3",
    )
    audio_file = audio_res["audio_path"]
    file_size = audio_res["file_size_kb"]
    print(f"      + Master MP3 broadcast file assembled ({file_size} KB).")

    print("\n" + "-" * 56)
    print(f"[OK] BROADCAST PACK COMPLETED FOR {ward.upper()}")
    print(f"     Script Text: {script_file}")
    print(f"     Audio File:  {audio_file}")
    print("-" * 56 + "\n")

    return {
        "ward": ward,
        "language": lang_code,
        "script": script_data,
        "script_file": str(script_file),
        "audio_file": str(audio_file),
        "file_size_kb": file_size,
    }


def main():
    """Command-line interface (CLI) for running PastroVoice Layer 3."""
    parser = argparse.ArgumentParser(
        description="PastroVoice Layer 3: Multimodal Radio Script and Speech Synthesizer"
    )
    parser.add_argument(
        "--ward",
        type=str,
        default="Laisamis",
        help="Target rangeland ward in Marsabit County (default: Laisamis)",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="sw",
        choices=["sw", "en", "kiswahili", "english"],
        help="Broadcast language ('sw' for Kiswahili, 'en' for English)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="output",
        help="Output folder for broadcast pack (default: output)",
    )
    parser.add_argument(
        "--key",
        type=str,
        default=None,
        help="Optional Gemini API key (defaults to GEMINI_API_KEY env)",
    )

    args = parser.parse_args()
    try:
        run_pastrovoice(
            ward=args.ward,
            lang=args.lang,
            output_dir=args.out,
            api_key=args.key,
        )
    except Exception as exc:
        logger.error("Broadcast generation failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
