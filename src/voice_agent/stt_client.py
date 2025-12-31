"""
STT Client for Modal IndicConformer service.
"""
import base64
import httpx
from .config import MODAL_STT_URL, LANGUAGE_CODE, STT_TIMEOUT


async def transcribe(audio_bytes: bytes, language: str = LANGUAGE_CODE) -> str:
    """
    Transcribe audio to text using Modal IndicConformer.
    
    Args:
        audio_bytes: WAV audio bytes (16-bit, mono, 16kHz)
        language: Language code (default: "kn" for Kannada)
    
    Returns:
        Transcription text
    """
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    async with httpx.AsyncClient(timeout=STT_TIMEOUT) as client:
        response = await client.post(
            f"{MODAL_STT_URL}/transcribe",
            json={
                "audio_b64": audio_b64,
                "language": language,
                "decoding": "ctc",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["transcription"]


async def health_check() -> dict:
    """Check STT service health."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{MODAL_STT_URL}/health")
        response.raise_for_status()
        return response.json()
