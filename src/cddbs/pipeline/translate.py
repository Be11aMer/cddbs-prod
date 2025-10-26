from src.cddbs.utils.genai_client import call_gemini

def translate_text(text: str, target_lang: str = 'en') -> str:
    """Translate text into target language using Gemini."""
    prompt = f"Translate the following text into {target_lang} while preserving meaning:\n\n{text}"
    try:
        return call_gemini(prompt)
    except Exception:
        return text
