import sys
import unittest
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))


class ExtractorImportsTest(unittest.TestCase):
    def test_retry_status_lookup_is_available(self):
        from phase3 import extractor

        self.assertTrue(callable(extractor.get_latest_extraction_status))

    def test_aggregate_payload_validation_rejects_missing_components(self):
        from phase3.extractor import _split_aggregate_result

        with self.assertRaises(ValueError):
            _split_aggregate_result({"knowledge_card": {"core_answer": "Only one part"}})

    def test_aggregate_payload_validation_accepts_list_data_points(self):
        from phase3.extractor import _split_aggregate_result

        card, methods, data_points = _split_aggregate_result({
            "knowledge_card": {"research_question": "RQ", "core_answer": "Answer"},
            "methods": {"workflow": []},
            "data_points": [{"metric_name": "Accuracy", "metric_value": 0.9}],
        })

        self.assertEqual("Answer", card["core_answer"])
        self.assertEqual([], methods["workflow"])
        self.assertEqual("Accuracy", data_points[0]["metric_name"])


class LlmJsonRepairTest(unittest.TestCase):
    def test_extracts_balanced_json_before_trailing_commentary(self):
        from phase3.llm_client import LLMClient

        result = LLMClient._parse_json('{"answer": {"value": 1}}\nExtraction complete.')

        self.assertEqual({"answer": {"value": 1}}, result)

    def test_repairs_only_missing_closing_delimiters(self):
        from phase3.llm_client import LLMClient

        result = LLMClient._parse_json(
            '{"knowledge_card": {}, "methods": {}, "data_points": []'
        )

        self.assertEqual([], result["data_points"])


def test_retry_runs_only_failed_component(monkeypatch):
    from phase3 import extractor

    calls = []
    monkeypatch.setattr(extractor, "get_failed_extraction_types", lambda paper_id: ["methods"])
    monkeypatch.setattr(
        extractor,
        "get_latest_extraction_status",
        lambda paper_id, extraction_type: {"status": "done"},
    )
    monkeypatch.setattr(
        extractor,
        "extract_methods",
        lambda paper_id, llm_client, **kwargs: calls.append("methods") or {"workflow": []},
    )
    monkeypatch.setattr(
        extractor,
        "extract_knowledge_card",
        lambda *args, **kwargs: calls.append("knowledge_card"),
    )
    monkeypatch.setattr(
        extractor,
        "extract_data_points",
        lambda *args, **kwargs: calls.append("data_points"),
    )

    result = extractor.extract_missing(9, llm_client=object())

    assert calls == ["methods"]
    assert result["methods"] == {"workflow": []}


if __name__ == "__main__":
    unittest.main()
