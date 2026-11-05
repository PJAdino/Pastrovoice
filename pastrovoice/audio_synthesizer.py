"""PastroVoice Layer 3: Text-to-Speech (TTS) Synthesizer and Audio Stitcher.

Converts multi-turn dialogue scripts into broadcast-ready MP3 audio files.
Uses Microsoft Edge TTS for authentic distinct Kenyan neural voices:
  - Host (Female Broadcaster): sw-KE-ZuriNeural / en-KE-AsiliaNeural
  - Expert (Male Officer):      sw-KE-RafikiNeural / en-KE-ChilembaNeural
Falls back to gTTS if edge-tts is unavailable.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Verified Kenyan Neural Voice Profiles
VOICE_MAP = {
    "sw": {
        "mtangazaji": "sw-KE-ZuriNeural",     # Female Kenyan Broadcaster (Fatuma Hassan)
        "mtaalamu": "sw-KE-RafikiNeural",     # Male Kenyan Extension Officer (Dr. Peter Leruk)
    },
    "en": {
        "mtangazaji": "en-KE-AsiliaNeural",   # Female Kenyan Broadcaster
        "mtaalamu": "en-KE-ChilembaNeural",   # Male Kenyan Extension Officer
    },
}


def _clean_spoken_text(text: str) -> str:
    """Prepare text for TTS pronunciation (strip asterisks, stage directions, etc.)."""
    cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", text)
    cleaned = cleaned.replace("*", "").replace("_", "")
    return cleaned.strip()


async def _synthesize_edge_tts(text: str, voice: str, output_path: Path) -> None:
    """Call Edge-TTS asynchronously to render audio using neural voice."""
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(str(output_path))


def synthesize_turn(
    text: str,
    speaker: str = "mtangazaji",
    lang: str = "sw",
    output_path: Optional[Path] = None,
) -> bytes:
    """Synthesize a single spoken line of dialogue into MP3 audio bytes.

    Uses authentic Kenyan female and male neural voices.
    """
    clean_text = _clean_spoken_text(text)
    if not clean_text:
        return b""

    tts_lang = "sw" if lang.lower() in ("sw", "kiswahili", "swahili") else "en"
    clean_speaker = "mtaalamu" if "mtaalamu" in speaker.lower() else "mtangazaji"
    voice = VOICE_MAP[tts_lang][clean_speaker]

    # Use Edge-TTS (True Male vs Female Kenyan Neural Voices)
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        asyncio.run(_synthesize_edge_tts(clean_text, voice, tmp_path))
        audio_bytes = tmp_path.read_bytes()
        try:
            tmp_path.unlink()
        except OSError:
            pass

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_bytes)

        return audio_bytes

    except Exception as exc:
        logger.info(
            "Edge-TTS unavailable (%s), using gTTS fallback.",
            type(exc).__name__,
        )
        # Fallback to gTTS if Edge-TTS network call fails
        from gtts import gTTS

        tts = gTTS(
            text=clean_text,
            lang=tts_lang,
            tld="co.ke" if clean_speaker == "mtangazaji" else "com",
        )
        mp3_buffer = io.BytesIO()
        tts.write_to_fp(mp3_buffer)
        audio_bytes = mp3_buffer.getvalue()

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_bytes)

        return audio_bytes


def synthesize_radio_broadcast(
    script_data: Dict[str, Any],
    output_dir: str | Path = "output",
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert an entire multi-turn dialogue script into a single broadcast MP3 file.

    Renders each speaker with their distinct studio voice (Female Host vs Male Expert).
    """
    ward = script_data.get("ward", "Marsabit")
    language = script_data.get("language", "Kiswahili")
    lang_code = "sw" if "swahili" in language.lower() else "en"
    dialogue_turns: List[Dict[str, str]] = script_data.get("dialogue", [])

    if not dialogue_turns:
        raise ValueError("Script data contains no dialogue turns to synthesize.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        clean_ward = ward.replace(" ", "_")
        filename = f"{clean_ward}_{lang_code}_advisory.mp3"

    master_path = out_dir / filename

    logger.info("Synthesizing dual-voice broadcast audio for %s (%s)...", ward, language)

    # Synthesize each turn sequentially and concatenate stream
    master_bytes = bytearray()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        for idx, turn in enumerate(dialogue_turns):
            speaker = turn.get("speaker", "mtangazaji")
            text = turn.get("text", "")
            turn_file = temp_path / f"turn_{idx:02d}.mp3"

            turn_bytes = synthesize_turn(
                text=text,
                speaker=speaker,
                lang=lang_code,
                output_path=turn_file,
            )
            master_bytes.extend(turn_bytes)

    # Write master broadcast file
    with open(master_path, "wb") as f:
        f.write(master_bytes)

    file_size_kb = round(os.path.getsize(master_path) / 1024, 2)
    logger.info("Dual-voice broadcast pack ready: %s (%.1f KB)", master_path, file_size_kb)

    return {
        "audio_path": str(master_path),
        "ward": ward,
        "language": language,
        "total_turns": len(dialogue_turns),
        "file_size_kb": file_size_kb,
    }
