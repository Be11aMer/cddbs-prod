import random
import time

from google import genai
from google.genai import types

from src.cddbs import settings
from src.cddbs.utils.system_prompt import get_system_prompt

# 3 retries with exponential backoff: 2s, 4s, 8s (+ ≤25% jitter each)
_RETRY_DELAYS = [2, 4, 8]

# Sentinel prefix returned (never raised) when every attempt fails.
GEMINI_ERROR_PREFIX = "[Gemini error:"


def is_gemini_error(response) -> bool:
    """True if `response` is the failure sentinel rather than real model output.

    call_gemini() never raises — it returns "[Gemini error: ...]" so callers can
    keep going. Any caller that *persists* model output must check this first,
    otherwise the error string gets stored as if it were a real analysis.
    """
    return isinstance(response, str) and response.lstrip().startswith(GEMINI_ERROR_PREFIX)


def call_gemini(prompt: str, api_key: str = None) -> str:
    """Generic Gemini prompt wrapper with 3-attempt exponential backoff retry."""
    gemini_key = api_key or settings.GOOGLE_API_KEY
    if not gemini_key:
        return f"{GEMINI_ERROR_PREFIX} No Google API key provided]"

    client = genai.Client(api_key=gemini_key)
    last_exc = None
    total_attempts = len(_RETRY_DELAYS) + 1  # 4 total (1 initial + 3 retries)

    for attempt in range(total_attempts):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=get_system_prompt(),
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
                contents=prompt,
            )
            return response.text
        except Exception as e:
            last_exc = e
            print(f"ERROR: Gemini API call failed (attempt {attempt + 1}/{total_attempts}): {e}")
            if attempt < len(_RETRY_DELAYS):
                delay = _RETRY_DELAYS[attempt]
                jitter = random.uniform(0, delay * 0.25)
                time.sleep(delay + jitter)

    return f"{GEMINI_ERROR_PREFIX} {last_exc}]"
