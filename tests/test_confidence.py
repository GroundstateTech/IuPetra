import csv
import json
import tempfile
import unittest
from pathlib import Path

from confidence import build_confidence_audit


class ConfidenceAuditTests(unittest.TestCase):
    def _write_csv(self, path: Path, headers, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    def test_builds_auditable_candidate_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "data" / "raw"
            raw.mkdir(parents=True)
            (raw / "fireballs.json").write_text("{}", encoding="utf-8")

            self._write_csv(
                root / "reports" / "01_EVIDENCE_REVIEW" / "watchlist_explained.csv",
                ["rank", "candidate_id", "candidate_name", "candidate_type", "score", "supporting_evidence", "source_report"],
                [{
                    "rank": "1",
                    "candidate_id": "OBJ-1",
                    "candidate_name": "Test Object",
                    "candidate_type": "repeat_object",
                    "score": "72",
                    "supporting_evidence": "Repeated close approaches in configured interval.",
                    "source_report": "repeating_close_approach_objects.csv",
                }],
            )

            self._write_csv(
                root / "reports" / "03_ORBIT_CONTEXT" / "candidate_orbit_review.csv",
                ["candidate_id", "orbit_context_status", "orbit_class_code", "orbit_class_name", "is_neo", "is_pha", "moid_au", "estimated_diameter_km", "sentry_match_status", "sentry_impact_probability"],
                [{
                    "candidate_id": "OBJ-1",
                    "orbit_context_status": "ok",
                    "orbit_class_code": "APO",
                    "orbit_class_name": "Apollo",
                    "is_neo": "true",
                    "is_pha": "false",
                    "moid_au": "0.012",
                    "estimated_diameter_km": "0.2",
                    "sentry_match_status": "no_match",
                    "sentry_impact_probability": "",
                }],
            )

            provenance = root / "reports" / "99_TECHNICAL_LOGS" / "run_provenance.json"
            provenance.parent.mkdir(parents=True, exist_ok=True)
            provenance.write_text(json.dumps({"raw_sources": []}), encoding="utf-8")

            output = build_confidence_audit(root)
            self.assertTrue(output.exists())
            rows = list(csv.DictReader(output.open("r", encoding="utf-8", newline="")))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["candidate_id"], "OBJ-1")
            self.assertEqual(row["pattern_strength_band"], "high")
            self.assertEqual(row["orbit_context_band"], "very_high")
            self.assertIn("not an impact probability", row["interpretation"])
            self.assertTrue((root / "reports" / "00_START_HERE" / "SCIENTIFIC_CONFIDENCE_README.txt").exists())

    def test_missing_context_is_flagged_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_csv(
                root / "reports" / "01_EVIDENCE_REVIEW" / "watchlist_explained.csv",
                ["rank", "candidate_id", "candidate_name", "candidate_type", "score", "supporting_evidence", "source_report"],
                [{
                    "rank": "1",
                    "candidate_id": "WINDOW-1",
                    "candidate_name": "Test Window",
                    "candidate_type": "window",
                    "score": "35",
                    "supporting_evidence": "Temporal clustering.",
                    "source_report": "",
                }],
            )
            output = build_confidence_audit(root)
            rows = list(csv.DictReader(output.open("r", encoding="utf-8", newline="")))
            flags = rows[0]["uncertainty_flags"]
            self.assertIn("source_quality_limit", flags)
            self.assertIn("orbit_context_incomplete", flags)
            self.assertIn("sentry_status_unavailable", flags)


if __name__ == "__main__":
    unittest.main()
