"""Input sanitization for prompt injection prevention.

Defense-in-depth layer that sanitizes user-provided text before it is
interpolated into LLM prompts.  This is NOT a guarantee against prompt
injection — the primary protections are:
  1. Gemini's system_instruction is set via API parameter (not injectable)
  2. JSON output format constrains response structure
  3. Output validation catches unexpected response format

This module strips control characters, normalizes whitespace, escapes
prompt-delimiter sequences, and truncates to configured limits.

OWASP LLM Top 10 — LLM01 (Prompt Injection)
"""

import re
import unicodedata

# Maximum lengths for different input types
MAX_TOPIC_LENGTH = 300
MAX_OUTLET_LENGTH = 200
MAX_HANDLE_LENGTH = 100
MAX_COUNTRY_LENGTH = 100

# Patterns that look like prompt override attempts
_INJECTION_PATTERNS = re.compile(
    r"(?i)"
    r"(?:ignore|disregard|override|forget|bypass)\s+"
    r"(?:all\s+)?(?:previous|above|prior|earlier|system|instructions?|rules?|prompts?)",
    re.IGNORECASE,
)

# Control characters and zero-width characters to strip
_CONTROL_CHARS = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f"  # ASCII control chars (keep \t \n \r)
    r"\u200b-\u200f"   # zero-width spaces and directional marks
    r"\u202a-\u202e"   # LTR/RTL embedding and overrides
    r"\u2060-\u2064"   # word joiners and invisible operators
    r"\ufeff"          # BOM / zero-width no-break space
    r"\ufff9-\ufffb"   # interlinear annotation anchors
    r"]"
)

# Triple-quote and long-dash sequences used as prompt delimiters
_TRIPLE_QUOTES = re.compile(r'"{3,}')
_TRIPLE_BACKTICKS = re.compile(r"`{3,}")
_LONG_DASHES = re.compile(r"-{3,}")


def sanitize_text(text: str, max_length: int) -> str:
    """Core sanitization: strip, normalize, escape, truncate."""
    if not text or not isinstance(text, str):
        return ""

    # 1. Strip control characters and zero-width chars
    result = _CONTROL_CHARS.sub("", text)

    # 2. Normalize unicode (NFC) to prevent homoglyph attacks
    result = unicodedata.normalize("NFC", result)

    # 3. Normalize whitespace (collapse runs, strip leading/trailing)
    result = " ".join(result.split())

    # 4. Escape prompt-delimiter sequences
    result = _TRIPLE_QUOTES.sub('""', result)
    result = _TRIPLE_BACKTICKS.sub("``", result)
    result = _LONG_DASHES.sub("--", result)

    # 5. Remove prompt injection patterns
    result = _INJECTION_PATTERNS.sub("[FILTERED]", result)

    # 6. Truncate to max length
    if len(result) > max_length:
        result = result[:max_length]

    return result.strip()


def sanitize_topic(topic: str) -> str:
    """Sanitize a topic string for use in Topic Mode prompts."""
    return sanitize_text(topic, MAX_TOPIC_LENGTH)


def sanitize_outlet(outlet: str) -> str:
    """Sanitize an outlet name for use in analysis prompts."""
    return sanitize_text(outlet, MAX_OUTLET_LENGTH)


def sanitize_handle(handle: str) -> str:
    """Sanitize a social media handle."""
    result = sanitize_text(handle, MAX_HANDLE_LENGTH)
    # Handles should only contain alphanumeric, underscores, dots, @
    result = re.sub(r"[^\w.@-]", "", result)
    return result


def sanitize_country(country: str) -> str:
    """Sanitize a country name."""
    result = sanitize_text(country, MAX_COUNTRY_LENGTH)
    # Country names: letters, spaces, hyphens, apostrophes
    result = re.sub(r"[^\w\s'-]", "", result)
    return result
