import json
from src.cddbs.utils.genai_client import call_gemini

def summarize_digest(outlet: str, country: str, digest: dict) -> str:
    """
    Generate a structured intelligence briefing summary for a given outlet and digest data.
    Uses Gemini with the system prompt for consistent analytical standards.
    """
    # Serialize digest data safely
    digest_json = json.dumps(digest, ensure_ascii=False, indent=2)

    prompt = f"""
    Create a structured analyst briefing based on the following digested disinformation analysis data.

    Outlet: {outlet}
    Country: {country}

    Data:
    {digest_json}

    Follow the reporting standards from your system instructions.
    Output should include:
    1. Outlet and Source URL
    2. Main Narrative / Claims (quoted or paraphrased with attribution)
    3. Analysis (disinformation pattern, tone, framing)
    4. Credibility Notes (confidence, missing sources, verification needs)
    """

    result = call_gemini(prompt)
    return result
