"""
TTS Client for Modal IndicF5 service.
"""
import httpx
from .config import MODAL_TTS_URL, TTS_TIMEOUT


async def synthesize(text: str, ref_audio_b64: str = None, ref_text: str = None) -> bytes:
    """
    Synthesize speech from text using Modal IndicF5.
    
    Args:
        text: Text to speak (Kannada)
        ref_audio_b64: Optional reference audio for voice cloning (base64)
        ref_text: Optional transcript of reference audio
    
    Returns:
        WAV audio bytes
    """
    payload = {"text": text}
    if ref_audio_b64:
        payload["ref_audio"] = ref_audio_b64
    if ref_text:
        payload["ref_text"] = ref_text
    
    async with httpx.AsyncClient(timeout=TTS_TIMEOUT) as client:
        response = await client.post(
            MODAL_TTS_URL,
            json=payload,
        )
        response.raise_for_status()
        return response.content  # WAV audio bytes
