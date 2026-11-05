"""Layer 4 HTTP API and browser IVR simulator."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.staticfiles import StaticFiles

from .catalog import Broadcast, discover_broadcasts
from .packs import build_radio_pack

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(os.environ.get("PASTROVOICE_OUTPUT_DIR", PROJECT_ROOT / "output")).resolve()
STATIC_DIR = Path(__file__).with_name("static")

app = FastAPI(
    title="PastroVoice Layer 4 Delivery",
    description="Radio station packs and a browser-based IVR demonstration.",
    version="0.1.0",
)
_cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "PASTROVOICE_DELIVERY_CORS_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.mount("/delivery-assets", StaticFiles(directory=STATIC_DIR), name="delivery-assets")


class Keypress(BaseModel):
    node: Literal["language", "ward", "playback"] = "language"
    language: Literal["sw", "en"] | None = None
    ward_code: str | None = None
    digit: str = Field(pattern=r"^[0-9*#]$")


def _get_broadcasts() -> list[Broadcast]:
    return discover_broadcasts(OUTPUT_DIR)


def _ward_options(language: str, broadcasts: list[Broadcast]) -> list[Broadcast]:
    return sorted((b for b in broadcasts if b.language == language), key=lambda b: b.ward.casefold())


def _broadcast_for_code(code: str, language: str | None = None) -> Broadcast:
    for item in _get_broadcasts():
        if item.ward_code == code and (language is None or item.language == language):
            return item
    raise HTTPException(status_code=404, detail="No matching broadcast is available")


def _choice_menu(items: list[Broadcast], language_name: str) -> dict:
    options = [{"digit": str(i + 1), "ward": item.ward, "ward_code": item.ward_code} for i, item in enumerate(items[:9])]
    return {
        "node": "ward",
        "prompt": f"Choose a ward for the {language_name} advisory.",
        "options": options,
        "audio_url": None,
    }


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "layer": 4, "broadcast_count": len(_get_broadcasts())}


@app.get("/api/catalog")
def catalog():
    return {"broadcasts": [b.public_dict() for b in _get_broadcasts()]}


@app.get("/api/audio/{ward_code}/{language}")
def audio(ward_code: str, language: Literal["sw", "en"]):
    item = _broadcast_for_code(ward_code, language)
    return FileResponse(item.audio_path, media_type="audio/mpeg", filename=item.audio_path.name)


@app.get("/api/cue-sheet/{ward_code}/{language}")
def cue_sheet(ward_code: str, language: Literal["sw", "en"]):
    item = _broadcast_for_code(ward_code, language)
    return FileResponse(item.script_path, media_type="application/json", filename=item.script_path.name)


@app.get("/api/radio-packs/{ward_code}/{language}.zip")
def radio_pack(ward_code: str, language: Literal["sw", "en"]):
    item = _broadcast_for_code(ward_code, language)
    return StreamingResponse(
        build_radio_pack(item),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{item.ward_code}_{language}_radio_pack.zip"'},
    )


@app.get("/ivr/{ward_code}/menu")
def ivr_menu(ward_code: str):
    broadcasts = [b for b in _get_broadcasts() if b.ward_code == ward_code]
    languages = sorted({b.language for b in broadcasts})
    if not languages:
        raise HTTPException(status_code=404, detail="No advisory is available for this ward")
    return {
        "node": "language",
        "ward_code": ward_code,
        "prompt": "Choose language: press 1 for Kiswahili, press 2 for English.",
        "options": [{"digit": "1", "language": "sw"}, {"digit": "2", "language": "en"}],
    }


@app.post("/ivr/keypress")
def ivr_keypress(event: Keypress):
    broadcasts = _get_broadcasts()
    if event.digit == "*":
        return {"node": "language", "prompt": "Choose language: press 1 for Kiswahili, press 2 for English.", "options": [{"digit": "1", "language": "sw"}, {"digit": "2", "language": "en"}], "audio_url": None}

    if event.node == "language":
        language = {"1": "sw", "2": "en"}.get(event.digit)
        if language is None:
            raise HTTPException(status_code=400, detail="Press 1 for Kiswahili or 2 for English")
        options = _ward_options(language, broadcasts)
        if not options:
            raise HTTPException(status_code=404, detail=f"No {language} advisories are available")
        return _choice_menu(options, "Kiswahili" if language == "sw" else "English") | {"language": language}

    if event.node == "ward":
        if event.language not in ("sw", "en"):
            raise HTTPException(status_code=400, detail="Choose a language first")
        options = _ward_options(event.language, broadcasts)[:9]
        index = int(event.digit) - 1 if event.digit.isdigit() else -1
        if index < 0 or index >= len(options):
            raise HTTPException(status_code=400, detail="That ward selection is not available")
        item = options[index]
        return {
            "node": "playback",
            "ward": item.ward,
            "ward_code": item.ward_code,
            "language": item.language,
            "prompt": f"Playing the latest {item.language_name} advisory for {item.ward}. Press 1 to replay or star to start again.",
            "audio_url": f"/api/audio/{item.ward_code}/{item.language}",
            "replay_digit": "1",
        }

    if event.node == "playback" and event.digit == "1" and event.ward_code:
        item = _broadcast_for_code(event.ward_code, event.language)
        return {"node": "playback", "ward": item.ward, "ward_code": item.ward_code, "language": item.language,
                "prompt": f"Replaying the advisory for {item.ward}.", "audio_url": f"/api/audio/{item.ward_code}/{item.language}", "replay_digit": "1"}
    raise HTTPException(status_code=400, detail="Press 1 to replay, or star to restart")
