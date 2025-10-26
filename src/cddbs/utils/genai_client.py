from google import genai
from google.genai import types
from src.cddbs.utils.system_prompt import get_system_prompt


def call_gemini(prompt: str) -> str:
    """Generic Gemini prompt wrapper."""
    client = genai.Client()

    try:
        response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=get_system_prompt(),
            temperature=0.1,
            thinking_config=types.ThinkingConfig(thinking_budget=-1)
        ),
        contents=prompt,
    )
        return str(response)
    except Exception as e:
        return f"[Gemini error: {e}]"