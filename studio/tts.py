from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Literal

Provider = Literal["edge", "openai", "none"]


def tts_provider_name() -> Provider:
    v = os.environ.get("TTS_PROVIDER", "edge").strip().lower()
    if v in ("edge", "openai", "none"):
        return v  # type: ignore[return-value]
    raise ValueError(f"Invalid TTS_PROVIDER={v!r}")


async def _edge_tts(text: str, out_mp3: Path) -> None:
    import edge_tts

    voice = os.environ.get("EDGE_TTS_VOICE", "en-US-GuyNeural").strip()
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_mp3))


def synthesize_narration(text: str, out_audio_mp3: Path) -> Path | None:
    """Write narration MP3 (ffmpeg-compatible), or return None if skipped."""
    text = text.strip()
    if not text:
        return None
    prov = tts_provider_name()
    if prov == "none":
        return None
    out_audio_mp3.parent.mkdir(parents=True, exist_ok=True)
    if prov == "edge":
        asyncio.run(_edge_tts(text, out_audio_mp3))
        return out_audio_mp3
    if prov == "openai":
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("OPENAI_API_KEY required for TTS_PROVIDER=openai")
        import httpx

        with httpx.Client(timeout=120.0) as client:
            r = client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": os.environ.get("OPENAI_TTS_VOICE", "alloy"),
                },
            )
            r.raise_for_status()
            out_audio_mp3.write_bytes(r.content)
        return out_audio_mp3
    return None
