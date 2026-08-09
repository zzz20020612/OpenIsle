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


if __name__ == "__main__":
    unittest.main()
