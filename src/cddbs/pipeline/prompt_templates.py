from src.cddbs.utils.system_prompt import get_system_prompt


def get_consolidated_prompt(outlet: str, country: str, articles_data: str) -> str:
    """Build the analysis prompt for a batch of articles.

    The system-level instructions (v1.3 enhanced prompt) are loaded separately
    via get_system_prompt() and passed as system_instruction to Gemini.
    This function builds the user-level prompt with the specific analysis task.
    """
    return f"""Analyze the following articles from outlet "{outlet}" ({country}).

Outlet: {outlet}
Country: {country}

Articles:
{articles_data}

STRICT RULES:
1. DO NOT invent claims, actors, or events.
2. ALWAYS attribute statements to their source (e.g., "According to {outlet}...").
3. Clearly separate facts (what the outlet published) from analysis (disinformation framing, propaganda, sentiment).
4. Use neutral, professional language (no creative writing).
5. IF an article contains unverifiable claims, mark them explicitly as "claim by {outlet}" or "unverified".

Output MUST be a valid JSON object with the following structure:
{{
  "individual_analyses": [
    {{
      "title": "Article Title",
      "link": "Article Link",
      "propaganda_score": 0.0-1.0,
      "sentiment": "positive/negative/neutral",
      "framing": "Description of the framing",
      "key_claims": ["Claim 1", "Claim 2"],
      "key_actors": ["Actor 1", "Actor 2"],
      "narrative_themes": ["Theme 1"],
      "unverified_statements": ["Statement 1"],
      "analysis_notes": "Brief analytical notes"
    }}
  ],
  "tldr_summary": "A 2-3 sentence high-level executive summary of the findings.",
  "final_briefing": "A structured intelligence briefing text incorporating all articles. Follow these sections:\\n1. Outlet and Source URL\\n2. Main Narrative/Claims\\n3. Analysis (patterns, tone, framing)\\n4. Credibility Notes"
}}

The goal is to generate a CREDIBLE analyst briefing that other professionals can rely on. DO NOT speculate. DO NOT embellish. Stick to cited sources.
"""
