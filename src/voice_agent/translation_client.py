"""
Translation Client for Modal IndicTrans2 services.
"""
import httpx
from .config import (
    MODAL_TRANS_INDIC_EN_URL,
    MODAL_TRANS_EN_INDIC_URL,
    LANGUAGE_SCRIPT,
    TRANSLATION_TIMEOUT,
)


async def translate_indic_to_english(text: str, src_lang: str = LANGUAGE_SCRIPT) -> str:
    """
    Translate Indic text (Kannada) to English.
    
    Args:
        text: Text in Indic language
        src_lang: Source language code (default: "kan_Knda")
    
    Returns:
        English translation
    """
    async with httpx.AsyncClient(timeout=TRANSLATION_TIMEOUT) as client:
        # Workaround for IndicTrans2 short text hallucination (outputs Hindi for short Kannada)
        input_text = text
        is_padded = False
        if src_lang == "kan_Knda" and len(text.split()) < 5:
            input_text = f"ನಮಸ್ಕಾರ, {text}"
            is_padded = True
            
        response = await client.post(
            f"{MODAL_TRANS_INDIC_EN_URL}/translate",
            json={
                "text": input_text,
                "src_lang": src_lang,
            },
        )
        response.raise_for_status()
        data = response.json()
        translation = data["translations"][0] if data["translations"] else ""
        
        # Optional: Clean up the padding from translation if we added it
        # "ನಮಸ್ಕಾರ" -> "Hello" / "Greetings" / "Salutations" / "Namaskar"
        if is_padded:
            # Simple heuristic: if translation starts with common greetings, we might strip them
            # But Agent handles "Hello, ..." fine.
            # Just ensuring we get English is the main goal.
            pass
            
        return translation


async def translate_english_to_indic(text: str, tgt_lang: str = LANGUAGE_SCRIPT) -> str:
    """
    Translate English text to Indic language (Kannada).
    
    Args:
        text: Text in English
        tgt_lang: Target language code (default: "kan_Knda")
    
    Returns:
        Indic language translation
    """
    async with httpx.AsyncClient(timeout=TRANSLATION_TIMEOUT) as client:
        response = await client.post(
            f"{MODAL_TRANS_EN_INDIC_URL}/translate",
            json={
                "text": text,
                "tgt_lang": tgt_lang,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["translations"][0] if data["translations"] else ""


async def health_check_indic_en() -> dict:
    """Check Indic→En translation service health."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{MODAL_TRANS_INDIC_EN_URL}/health")
        response.raise_for_status()
        return response.json()


async def health_check_en_indic() -> dict:
    """Check En→Indic translation service health."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{MODAL_TRANS_EN_INDIC_URL}/health")
        response.raise_for_status()
        return response.json()
