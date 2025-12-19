"""Audio handling stub for future media processing."""

from __future__ import annotations

from typing import Any, Dict


def transcribe(audio_source: str) -> Dict[str, Any]:
    """Return placeholder transcription data."""

    return {
        "status": "pending",
        "message": "Transcription not implemented",
        "source": audio_source,
    }
