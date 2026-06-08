"""Tests for the M-4 consistency-testing harness's analysis logic.

The harness (`scripts/consistency_test.py`) makes live Gemini calls and is not
run in CI — these tests cover its pure analysis functions (`summarize`,
`render_report`) against canned records, so the variance/threshold logic is
verified without needing a live GOOGLE_API_KEY.
"""
import importlib.util
import sys
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "consistency_test.py"
_spec = importlib.util.spec_from_file_location("consistency_test", _SCRIPT_PATH)
consistency_test = importlib.util.module_from_spec(_spec)
sys.modules["consistency_test"] = consistency_test
_spec.loader.exec_module(consistency_test)

summarize = consistency_test.summarize
render_report = consistency_test.render_report
VARIANCE_THRESHOLD_POINTS = consistency_test.VARIANCE_THRESHOLD_POINTS


def _record(run, score, signal="medium", techniques=None, raw="{}"):
    return {
        "run": run,
        "divergence_score": score,
        "amplification_signal": signal,
        "propaganda_techniques": techniques if techniques is not None else ["Loaded language"],
        "raw": raw,
    }


class TestSummarize:
    def test_computes_basic_statistics(self):
        records = [_record(i, score) for i, score in enumerate([50, 52, 48, 51, 49], start=1)]
        summary = summarize(records)

        assert summary["n_runs"] == 5
        assert summary["n_scored"] == 5
        assert summary["mean"] == 50.0
        assert summary["min"] == 48
        assert summary["max"] == 52
        assert summary["range"] == 4

    def test_flags_when_range_exceeds_threshold(self):
        records = [_record(i, score) for i, score in enumerate([20, 75], start=1)]
        summary = summarize(records)

        assert summary["range"] == 55
        assert summary["range"] > VARIANCE_THRESHOLD_POINTS
        assert summary["exceeds_threshold"] is True

    def test_does_not_flag_when_range_within_threshold(self):
        records = [_record(i, score) for i, score in enumerate([45, 50, 48], start=1)]
        summary = summarize(records)

        assert summary["range"] == 5
        assert summary["exceeds_threshold"] is False

    def test_handles_unscored_runs_gracefully(self):
        records = [
            _record(1, 50),
            {"run": 2, "divergence_score": None, "amplification_signal": None,
             "propaganda_techniques": None, "raw": "[Gemini error: timeout]"},
        ]
        summary = summarize(records)

        assert summary["n_runs"] == 2
        assert summary["n_scored"] == 1
        assert summary["mean"] == 50
        assert summary["range"] == 0

    def test_no_scored_runs_yields_none_statistics(self):
        records = [{"run": 1, "divergence_score": None, "amplification_signal": None,
                    "propaganda_techniques": None, "raw": "[Gemini error: timeout]"}]
        summary = summarize(records)

        assert summary["n_scored"] == 0
        assert summary["mean"] is None
        assert summary["exceeds_threshold"] is None

    def test_technique_stability_tracks_common_and_union(self):
        records = [
            _record(1, 50, techniques=["Loaded language", "Whataboutism"]),
            _record(2, 52, techniques=["Loaded language", "False equivalence"]),
        ]
        summary = summarize(records)

        assert summary["propaganda_techniques_common_to_all_runs"] == ["Loaded language"]
        assert summary["propaganda_techniques_union_across_runs"] == [
            "False equivalence", "Loaded language", "Whataboutism",
        ]

    def test_amplification_signal_distribution_counts_each_value(self):
        records = [_record(1, 50, signal="high"), _record(2, 52, signal="high"), _record(3, 48, signal="medium")]
        summary = summarize(records)

        assert summary["amplification_signal_distribution"] == {"high": 2, "medium": 1}


class TestRenderReport:
    def test_report_includes_threshold_verdict_when_exceeded(self):
        records = [_record(i, score) for i, score in enumerate([20, 75], start=1)]
        summary = summarize(records)
        report = render_report(records, summary)

        assert "**EXCEEDED**" in report
        assert "Recommendation triggered" in report

    def test_report_includes_within_threshold_message(self):
        records = [_record(i, score) for i, score in enumerate([45, 50, 48], start=1)]
        summary = summarize(records)
        report = render_report(records, summary)

        assert "within threshold" in report
        assert "appears stable enough" in report

    def test_report_includes_per_run_table_and_raw_appendix(self):
        records = [_record(1, 50, raw='{"divergence_score": 50}')]
        summary = summarize(records)
        report = render_report(records, summary)

        assert "| Run | divergence_score" in report
        assert "| 1 | 50 |" in report
        assert '{"divergence_score": 50}' in report
