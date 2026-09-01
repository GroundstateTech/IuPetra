import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("iupetra", ROOT / "iupetra.py")
iupetra = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(iupetra)


class CoreTests(unittest.TestCase):
    def test_standalone_contract_and_account_free_settings(self):
        self.assertTrue((ROOT / "docs" / "STANDALONE_OPERATION.md").is_file())
        payload = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
        self.assertNotIn("admin_center", payload)
        self.assertNotIn("identity_provider", payload)

    def test_settings_file_is_valid_object(self):
        payload = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict)
        for key in iupetra.DEFAULT_SETTINGS:
            self.assertIn(key, payload)

    def test_clean_report_value(self):
        self.assertEqual(iupetra.clean_report_value(" value "), "value")
        self.assertEqual(iupetra.clean_report_value("", "fallback"), "fallback")
        self.assertEqual(iupetra.clean_report_value(None), "not available")

    def test_settings_summary_mentions_configured_window(self):
        summary = iupetra.settings_summary_line()
        self.assertIn(iupetra.CLOSE_APPROACH_DATE_MIN, summary)
        self.assertIn(iupetra.CLOSE_APPROACH_DATE_MAX, summary)
        self.assertIn(iupetra.CLOSE_APPROACH_DISTANCE_MAX_AU, summary)

    def test_report_paths_stay_inside_project(self):
        for path in [
            iupetra.DATA_RAW_DIR,
            iupetra.DATA_CLEAN_DIR,
            iupetra.REPORTS_DIR,
            iupetra.PATH_DASHBOARD_HTML,
            iupetra.PATH_ERROR_LOG,
        ]:
            self.assertTrue(path.is_relative_to(iupetra.PROJECT_ROOT))


if __name__ == "__main__":
    unittest.main()
