"""Transcribe the seller's onboarding voice note with Gemini (multimodal).

Failure here must never block onboarding — the voice note is enrichment,
so any error returns None and the pipeline continues without it.
"""

import logging

from .config import LLM_MODEL, genai_client

log = logging.getLogger(__name__)

PROMPT = (
    "Transcribe this voice note from a secondhand-clothing reseller describing "
    "their shop. Return ONLY the clean transcript text — no preamble, no notes. "
    "Lightly fix filler words but keep their meaning and vocabulary."
)


def transcribe(audio_bytes: bytes, mime_type: str) -> str | None:
    from google.genai import types

    mime = (mime_type or "audio/webm").split(";")[0]
    try:
        resp = genai_client().models.generate_content(
            model=LLM_MODEL,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                PROMPT,
            ],
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception:
        log.exception("voice transcription failed (mime=%s) — continuing without it", mime)
        return None
