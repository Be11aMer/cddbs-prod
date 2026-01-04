from google import genai
from google.genai import types

from src.cddbs import settings
from src.cddbs.utils.system_prompt import get_system_prompt


def call_gemini(prompt: str, api_key: str = None) -> str:
    """Generic Gemini prompt wrapper."""
    gemini_key = api_key or settings.GOOGLE_API_KEY
    if not gemini_key:
        return "[Gemini error: No Google API key provided]"
        
    client = genai.Client(api_key=gemini_key)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=get_system_prompt(),
                temperature=0.1,
                response_mime_type="application/json",
            ),
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"ERROR: Gemini API call failed: {e}")
        return f"[Gemini error: {e}]"