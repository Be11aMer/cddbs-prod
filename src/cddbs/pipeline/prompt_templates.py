

def get_consolidated_prompt(outlet: str, country: str, articles_data: str) -> str:
    """Build the analysis prompt for a batch of articles.

    The system-level instructions (v1.3 enhanced prompt) are loaded separately
    via get_system_prompt() and passed as system_instruction to Gemini.
    This function builds the user-level prompt with the specific analysis task.

    Returns a structured 7-section intelligence briefing as JSON.
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
  "structured_briefing": {{
    "executive_summary": "A 3-5 sentence intelligence-grade executive summary. State the assessed nature of the outlet, primary concern, and overall confidence level.",
    "key_findings": [
      {{
        "finding": "Clear, specific finding statement (minimum 20 words).",
        "confidence": "high/moderate/low",
        "evidence_type": "PATTERN/EXTERNAL/NETWORK/POST/METADATA",
        "evidence": "Specific reference with metrics where applicable."
      }}
    ],
    "subject_profile": {{
      "name": "{outlet}",
      "platform": "web",
      "country": "{country}",
      "articles_analyzed": 0,
      "analysis_period": "date range",
      "description": "Brief description of the outlet",
      "language": "Primary language",
      "type": "State media / Independent / Proxy / Unknown"
    }},
    "narrative_analysis": {{
      "primary_narratives": [
        {{
          "narrative": "Narrative description",
          "frequency": "dominant/frequent/occasional",
          "alignment": "Known narrative alignment or independent description"
        }}
      ],
      "behavioral_indicators": [
        {{
          "indicator": "Indicator name (e.g., Publishing frequency)",
          "value": "Specific metric or observation"
        }}
      ],
      "network_context": [
        {{
          "label": "Context label (e.g., Known associations)",
          "value": "Details"
        }}
      ],
      "source_attribution": {{
        "role": "Official State Media / Proxy / Deniable / Authentic / Unknown",
        "content_origin": "Description of content origin",
        "amplification_chain": "Description of amplification chain if applicable"
      }}
    }},
    "confidence_assessment": {{
      "overall": "high/moderate/low",
      "factors": [
        {{
          "factor": "Data Completeness",
          "level": "high/moderate/low",
          "notes": "Assessment notes"
        }},
        {{
          "factor": "Source Reliability",
          "level": "high/moderate/low",
          "notes": "Assessment notes"
        }},
        {{
          "factor": "Analytical Consistency",
          "level": "high/moderate/low",
          "notes": "Assessment notes"
        }},
        {{
          "factor": "Corroboration",
          "level": "high/moderate/low",
          "notes": "Assessment notes"
        }}
      ]
    }},
    "limitations": [
      "Specific limitation or caveat with warning context"
    ],
    "methodology": {{
      "data_collection": "Method description",
      "articles_analyzed": 0,
      "analysis_period": "Date range",
      "analysis_model": "Model name and version",
      "prompt_version": "v1.3",
      "validation": "Cross-checking performed"
    }}
  }},
  "final_briefing": "A structured intelligence briefing text incorporating all articles. Follow these sections:\\n1. Outlet and Source URL\\n2. Main Narrative/Claims\\n3. Analysis (patterns, tone, framing)\\n4. Credibility Notes"
}}

IMPORTANT: The "structured_briefing" object is the PRIMARY output. Fill ALL 7 sections with specific, data-driven content based on the articles analyzed. The "final_briefing" field is kept for backward compatibility.

The goal is to generate a CREDIBLE analyst briefing that other professionals can rely on. DO NOT speculate. DO NOT embellish. Stick to cited sources.
"""


def get_social_media_prompt(platform: str, handle: str, profile_data: str, posts_data: str) -> str:
    """Build the analysis prompt for social media account analysis.

    Used by the social media analysis pipeline (Twitter/Telegram).
    The system prompt v1.3 already contains platform-specific instructions.
    """
    return f"""Analyze the following {platform} account: {handle}

Platform: {platform}

Profile Data:
{profile_data}

Recent Posts/Messages:
{posts_data}

STRICT RULES:
1. DO NOT invent claims, actors, or events.
2. ALWAYS attribute statements to their source.
3. Clearly separate observed facts from analytical inferences.
4. Use professional attribution language only.

Output MUST be a valid JSON object with the following structure:
{{
  "individual_analyses": [
    {{
      "title": "Post/message summary",
      "link": "",
      "propaganda_score": 0.0-1.0,
      "sentiment": "positive/negative/neutral",
      "framing": "Description of the framing",
      "key_claims": ["Claim 1"],
      "key_actors": ["Actor 1"],
      "narrative_themes": ["Theme 1"],
      "unverified_statements": ["Statement 1"],
      "analysis_notes": "Brief analytical notes"
    }}
  ],
  "tldr_summary": "A 2-3 sentence high-level executive summary.",
  "structured_briefing": {{
    "executive_summary": "3-5 sentence intelligence-grade summary of the account. State assessed nature, primary concern, overall confidence.",
    "key_findings": [
      {{
        "finding": "Clear finding statement (min 20 words).",
        "confidence": "high/moderate/low",
        "evidence_type": "PATTERN/EXTERNAL/NETWORK/POST/METADATA/FORWARD/CHANNEL_META",
        "evidence": "Specific reference with metrics."
      }}
    ],
    "subject_profile": {{
      "name": "{handle}",
      "platform": "{platform}",
      "country": "",
      "articles_analyzed": 0,
      "analysis_period": "date range",
      "description": "Account bio/description",
      "language": "Primary language",
      "type": "State media / Proxy / Deniable / Authentic / Unknown",
      "followers": 0,
      "following": 0,
      "verified": false
    }},
    "narrative_analysis": {{
      "primary_narratives": [
        {{
          "narrative": "Narrative description",
          "frequency": "dominant/frequent/occasional",
          "alignment": "Known narrative ID or independent"
        }}
      ],
      "behavioral_indicators": [
        {{
          "indicator": "Indicator name",
          "value": "Specific metric"
        }}
      ],
      "network_context": [
        {{
          "label": "Context label",
          "value": "Details"
        }}
      ],
      "source_attribution": {{
        "role": "Official State Media / Proxy / Deniable / Authentic / Unknown",
        "content_origin": "Description",
        "amplification_chain": "Description if applicable"
      }}
    }},
    "confidence_assessment": {{
      "overall": "high/moderate/low",
      "factors": [
        {{
          "factor": "Data Completeness",
          "level": "high/moderate/low",
          "notes": "Notes"
        }},
        {{
          "factor": "Source Reliability",
          "level": "high/moderate/low",
          "notes": "Notes"
        }},
        {{
          "factor": "Analytical Consistency",
          "level": "high/moderate/low",
          "notes": "Notes"
        }},
        {{
          "factor": "Corroboration",
          "level": "high/moderate/low",
          "notes": "Notes"
        }}
      ]
    }},
    "limitations": [
      "Specific limitation"
    ],
    "methodology": {{
      "data_collection": "{platform} API",
      "articles_analyzed": 0,
      "analysis_period": "Date range",
      "analysis_model": "Model name",
      "prompt_version": "v1.3",
      "validation": "Cross-checking performed"
    }}
  }},
  "final_briefing": "Backward-compatible text briefing with sections: 1. Source, 2. Narrative, 3. Analysis, 4. Credibility Notes"
}}

Follow the system prompt instructions for {platform}-specific analysis. Fill ALL 7 sections of structured_briefing with specific, data-driven content.
"""
