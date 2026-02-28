from pathlib import Path

_PROMPT_PATH = Path(__file__).parent.parent / "data" / "system_prompt_v1.3.txt"
_cached_prompt = None


def get_system_prompt() -> str:
    """Load v1.3 system prompt from file (cached after first load)."""
    global _cached_prompt
    if _cached_prompt is None:
        _cached_prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    return _cached_prompt
