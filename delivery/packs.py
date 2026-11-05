"""Build portable radio-station ZIP packs from Layer 3 output files."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .catalog import Broadcast


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_radio_pack(broadcast: Broadcast) -> io.BytesIO:
    """Return an in-memory ZIP containing audio, cue sheet and station notes."""
    script = json.loads(broadcast.script_path.read_text(encoding="utf-8"))
    manifest = {
        "product": "PastroVoice radio station pack",
        "ward": broadcast.ward,
        "language": broadcast.language,
        "language_name": broadcast.language_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Layer 3 generated broadcast",
        "files": {
            broadcast.audio_path.name: {"bytes": broadcast.audio_path.stat().st_size, "sha256": _sha256(broadcast.audio_path)},
            broadcast.script_path.name: {"bytes": broadcast.script_path.stat().st_size, "sha256": _sha256(broadcast.script_path)},
        },
    }
    notes = (
        f"PastroVoice radio pack\nWard: {broadcast.ward}\n"
        f"Language: {broadcast.language_name} ({broadcast.language})\n\n"
        "Broadcast the MP3 as supplied. The JSON cue sheet contains the presenter dialogue. "
        "Check the ward and language before transmission. Follow your station's normal "
        "editorial and scheduling process.\n"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(broadcast.audio_path, broadcast.audio_path.name)
        archive.write(broadcast.script_path, broadcast.script_path.name)
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("README.txt", notes)
    buffer.seek(0)
    return buffer
