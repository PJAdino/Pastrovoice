"""PastroVoice: Multimodal Audio Early Warning & Command Engine for Pastoralist Communities.

Layer 3: Script Generation (LLM) and Text-to-Speech Synthesis (TTS).
Layer 2 Bridge: Automated database-to-payload mapper.
"""

from .payload import validate_payload, load_sample_payload, InvalidPayloadError
from .script_generator import generate_radio_script, build_prompt
from .audio_synthesizer import synthesize_turn, synthesize_radio_broadcast
from .engine import run_pastrovoice
from .bridge import build_advisory_payload_from_db

__all__ = [
    "run_pastrovoice",
    "build_advisory_payload_from_db",
    "validate_payload",
    "load_sample_payload",
    "InvalidPayloadError",
    "generate_radio_script",
    "build_prompt",
    "synthesize_turn",
    "synthesize_radio_broadcast",
]
