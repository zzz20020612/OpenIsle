from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from search import api


class _Progress:
    def __init__(self):
        self.updates = []

    def set_progress(self, progress, message=""):
        self.updates.append((progress, message))


class CompletePipelineTest(unittest.TestCase):
    @patch.object(api, "_extract_task")
    @patch.object(api, "_parse_task")
    @patch.object(api, "_collect_task")
    def test_existing_metadata_continues_to_parse_and_extract(
        self, collect, parse, extract
    ):
        collect.return_value = {"inserted": 0, "paper_ids": [17]}
        parse.return_value = {"success": 1, "skipped": 0, "failed": 0}
        extract.return_value = {
            "papers": 1,
            "knowledge_cards": 1,
            "methods": 1,
            "data_points": 2,
            "errors": 0,
        }

        result = api._pipeline_task(
            _Progress(), "soil carbon", 20, 2, "", "", "", "all", 15
        )

        parse.assert_called_once()
        extract.assert_called_once_with(unittest.mock.ANY, paper_ids=[17])
        self.assertEqual(1, result["extract"]["knowledge_cards"])

    @patch.object(api, "_extract_task")
    @patch.object(api, "_parse_task")
    @patch.object(api, "_collect_task")
    def test_no_search_results_finishes_without_downstream_work(
        self, collect, parse, extract
    ):
        collect.return_value = {"inserted": 0, "paper_ids": []}

        result = api._pipeline_task(
            _Progress(), "missing topic", 20, 2, "", "", "", "all", 15
        )

        parse.assert_not_called()
        extract.assert_not_called()
        self.assertEqual({}, result["parse"])

    @patch.object(api, "_sync_search_papers")
    @patch("collect.oa_import.fetch_and_import")
    def test_open_source_collection_returns_ids_for_downstream_stages(
        self, fetch_and_import, sync_search
    ):
        fetch_and_import.return_value = {
            "source": "arxiv",
            "processed": 2,
            "paper_ids": [31, 32],
        }

        result = api._collect_task(
            _Progress(), "graph neural networks", 10, 1, "", "", "", "arxiv"
        )

        self.assertEqual([31, 32], result["paper_ids"])
        self.assertEqual(2, result["inserted"])
        sync_search.assert_called_once_with([31, 32])
        fetch_and_import.assert_called_once_with(
            "arxiv",
            "graph neural networks",
            10,
            1,
            start_date=None,
            end_date=None,
            return_details=True,
        )

    @patch.object(api, "_sync_search_papers")
    @patch("collect.oa_import.fetch_and_import")
    @patch("collect.multi_source_collector.run_collection")
    def test_all_open_collection_keeps_successes_when_one_source_fails(
        self, run_collection, fetch_and_import, sync_search
    ):
        run_collection.return_value = {"inserted": 1, "paper_ids": [41]}

        def source_result(source, *_args, **_kwargs):
            if source == "pmc":
                raise RuntimeError("temporary upstream failure")
            return {"source": source, "processed": 1, "paper_ids": [50]}

        fetch_and_import.side_effect = source_result

        result = api._collect_task(
            _Progress(), "climate adaptation", 5, 1, "", "", "", "all_open"
        )

        self.assertEqual([41, 50], result["paper_ids"])
        self.assertIn("error", result["per_source"]["pmc"])
        sync_search.assert_called_once_with([41, 50])


if __name__ == "__main__":
    unittest.main()
