"""Prompt templates for Topic Mode analysis.

Topic Mode flow:
  1. get_baseline_prompt()   → neutral reference summary from reputable wire services
  2. get_comparative_prompt() → per-outlet divergence analysis vs. the baseline
"""


def get_baseline_prompt(topic: str, articles_data: str) -> str:
    """Build the prompt that produces a neutral baseline from wire-service coverage.

    The Gemini system prompt (system_instruction) is set separately.
    This user-level prompt provides the specific task.
    """
    return f"""You are an intelligence analyst establishing a neutral factual baseline.

TOPIC: "{topic}"

The following articles are from established wire services (Reuters, BBC, AP, AFP) that
are widely recognised as neutral reference sources with no significant geopolitical editorial line.

Articles:
{articles_data}

STRICT RULES:
1. DO NOT invent claims, actors, or events not present in the articles.
2. Report only what these neutral sources actually say about the topic.
3. Use neutral, professional language. No editorialising.
4. If the articles contain conflicting facts, note the conflict.
5. This baseline will be used to compare other outlets against — accuracy is critical.

Produce a valid JSON object:
{{
  "baseline_summary": "A clear 3-5 sentence factual summary of how neutral wire services report on this topic. This is the ground truth.",
  "key_facts": ["Verified fact 1", "Verified fact 2", "..."],
  "neutral_framing": "How neutral sources frame this topic: what angle, what emphasis, what actors they highlight.",
  "topics_covered": ["Sub-topic or angle 1", "Sub-topic or angle 2"]
}}

The goal is a credible, citable baseline that professionals can use to detect framing divergence in other outlets.
"""


def get_comparative_prompt(
    topic: str,
    baseline_summary: str,
    outlet_domain: str,
    articles_data: str,
) -> str:
    """Build the comparative prompt for a single discovered outlet.

    Compares the outlet's coverage of the topic against the pre-computed neutral baseline.
    """
    return f"""You are an intelligence analyst specialising in information operations and narrative detection.

TOPIC: "{topic}"

NEUTRAL BASELINE (from Reuters, BBC, AP, AFP wire services):
{baseline_summary}

OUTLET UNDER ANALYSIS: {outlet_domain}

The following articles are from this outlet on the same topic:
{articles_data}

STRICT RULES:
1. DO NOT invent claims. Only analyse what is present in the outlet's articles.
2. Attribute all statements to their source (e.g., "According to {outlet_domain}...").
3. Compare only against the neutral baseline provided — do not bring in external knowledge.
4. Use professional, neutral analytical language.
5. The divergence_score must reflect genuine framing differences, not style differences.
   - 0-20: Largely aligned with neutral baseline, minor emphasis differences
   - 21-40: Noticeable framing divergence, selective emphasis or omission
   - 41-60: Significant narrative divergence, loaded language or systematic omission of key facts
   - 61-80: Strong narrative pushing, clear departure from neutral framing, possible propaganda techniques
   - 81-100: Extreme divergence, likely coordinated narrative, overt disinformation signals

Produce a valid JSON object:
{{
  "divergence_score": <integer 0-100>,
  "amplification_signal": "<low|medium|high>",
  "propaganda_techniques": ["Technique 1", "Technique 2"],
  "framing_summary": "2-3 sentence description of how this outlet frames the topic differently from the neutral baseline.",
  "divergence_explanation": "Specific explanation of what diverges and why it is analytically significant. Cite specific claims from the articles.",
  "key_claims_by_outlet": ["Specific claim 1 made by this outlet", "..."],
  "omissions": ["Key fact from baseline that this outlet omits or downplays"]
}}

Amplification signal criteria:
- high: outlet has multiple articles on this topic, far more coverage than the topic's newsworthiness warrants
- medium: topic is covered, somewhat more than baseline sources
- low: coverage volume is proportionate to the topic's importance

The goal is a credible analyst assessment, not speculation. Only score high if the evidence in the articles supports it.
"""
