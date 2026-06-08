"""Tests for the propaganda-technique taxonomy normaliser (audit M-1).

Verifies that synonymous free-text tags returned by Gemini ("loaded language"
vs "emotionally loaded terminology") collapse onto the same closed-taxonomy
code, which is what allows the coordination signal to match techniques across
outlets reliably.
"""
from src.cddbs.pipeline.technique_taxonomy import (
    normalize_technique,
    normalize_techniques,
    normalized_codes,
)


class TestNormalizeTechnique:
    def test_exact_alias_match(self):
        assert normalize_technique("Whataboutism")["code"] == "whataboutism"
        assert normalize_technique("what-aboutism")["code"] == "whataboutism"

    def test_synonymous_phrasings_collapse_to_same_code(self):
        variants = ["Loaded language", "loaded rhetoric", "emotionally loaded terminology"]
        codes = {normalize_technique(v)["code"] for v in variants}
        assert codes == {"loaded_language"}

    def test_case_and_whitespace_insensitive(self):
        assert normalize_technique("  WHATABOUTISM  ")["code"] == "whataboutism"

    def test_unknown_technique_returns_none(self):
        assert normalize_technique("Some completely fictional technique xyz123") is None

    def test_empty_input_returns_none(self):
        assert normalize_technique("") is None
        assert normalize_technique("   ") is None
        assert normalize_technique(None) is None

    def test_preserves_raw_tag(self):
        result = normalize_technique("emotionally loaded terminology")
        assert result["raw"] == "emotionally loaded terminology"
        assert result["name"] == "Loaded Language"


class TestNormalizeTechniques:
    def test_drops_unmatched_tags(self):
        result = normalize_techniques(["Whataboutism", "Some made-up nonsense", "False equivalence"])
        codes = [r["code"] for r in result]
        assert codes == ["whataboutism", "false_equivalence"]

    def test_handles_empty_and_none_input(self):
        assert normalize_techniques([]) == []
        assert normalize_techniques(None) == []


class TestNormalizedCodes:
    def test_synonyms_yield_single_unique_code(self):
        codes = normalized_codes(["Loaded language", "emotionally loaded terminology", "Whataboutism"])
        assert codes == ["loaded_language", "whataboutism"]

    def test_coordination_matching_scenario(self):
        """Two outlets using synonymous phrasing for the same techniques should
        now be detected as sharing techniques — the defect M-1 was filed against."""
        outlet_a_codes = set(normalized_codes(["Loaded language", "Whataboutism"]))
        outlet_b_codes = set(normalized_codes(["emotionally loaded terminology", "what-aboutism"]))
        assert outlet_a_codes == outlet_b_codes == {"loaded_language", "whataboutism"}
