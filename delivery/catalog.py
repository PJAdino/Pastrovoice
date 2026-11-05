"""Discover paired Layer 3 audio and cue-sheet artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Broadcast:
    ward: str
    ward_code: str
    language: str
    language_name: str
    audio_path: Path
    script_path: Path

    def public_dict(self) -> dict[str, str]:
        return {
            "ward": self.ward,
            "ward_code": self.ward_code,
            "language": self.language,
            "language_name": self.language_name,
            "audio_url": f"/api/audio/{self.ward_code}/{self.language}",
            "script_url": f"/api/cue-sheet/{self.ward_code}/{self.language}",
            "pack_url": f"/api/radio-packs/{self.ward_code}/{self.language}.zip",
        }


def ward_code(ward: str) -> str:
    """Convert a ward label into a stable URL-safe code."""
    code = re.sub(r"[^a-z0-9]+", "-", ward.casefold()).strip("-")
    if not code:
        raise ValueError("Ward name must contain letters or numbers")
    return code


def discover_broadcasts(output_dir: Path) -> list[Broadcast]:
    """Return only complete MP3 + JSON pairs produced by Layer 3."""
    if not output_dir.exists():
        return []
    found: list[Broadcast] = []
    for script_path in sorted(output_dir.glob("*_script.json")):
        stem = script_path.name.removesuffix("_script.json")
        if not stem.endswith(("_sw", "_en")):
            continue
        language = stem[-2:]
        audio_path = output_dir / f"{stem}_advisory.mp3"
        if not audio_path.is_file() or not audio_path.stat().st_size:
            continue
        try:
            script = json.loads(script_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ward = str(script.get("ward", "")).strip()
        if not ward or not isinstance(script.get("dialogue"), list):
            continue
        found.append(Broadcast(
            ward=ward,
            ward_code=ward_code(ward),
            language=language,
            language_name=str(script.get("language") or ("Kiswahili" if language == "sw" else "English")),
            audio_path=audio_path,
            script_path=script_path,
        ))
    return found


def find_broadcast(output_dir: Path, ward: str, language: str) -> Broadcast:
    code = ward_code(ward)
    for item in discover_broadcasts(output_dir):
        if item.ward_code == code and item.language == language:
            return item
    raise FileNotFoundError(f"No complete {language} broadcast is available for {ward}")
