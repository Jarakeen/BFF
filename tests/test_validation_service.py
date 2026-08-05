# tests/test_validation_service.py
import json
import tempfile
import unittest
from pathlib import Path

from services.validation_service import ValidationService


class ValidationServiceTests(unittest.TestCase):
    def test_validation_reports_duplicates_and_invalid_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "skills.json").write_text(
                json.dumps(
                    [
                        {"id": "skill_1", "name": "Skill One"},
                        {"id": "skill_1", "name": "Skill Two"},
                        {"name": "Missing Id"},
                    ]
                ),
                encoding="utf-8",
            )
            (data_dir / "gear_sets.json").write_text(
                json.dumps([
                    {"id": "set_1", "name": "Set One", "required_effects": ["Missing Effect"]}
                ]),
                encoding="utf-8",
            )
            (data_dir / "status_effects.json").write_text(
                json.dumps([{"id": "effect_1", "name": "Major Courage"}]),
                encoding="utf-8",
            )

            service = ValidationService(data_dir)
            report = service.validate_directory()

            self.assertFalse(report["is_valid"])
            self.assertEqual(report["summary"]["total_records"], 5)
            self.assertGreaterEqual(len(report["issues"]), 2)
            self.assertTrue(any(issue["type"] == "duplicate_id" for issue in report["issues"]))
            self.assertTrue(any(issue["type"] == "invalid_reference" for issue in report["issues"]))
            self.assertTrue((data_dir / "validation_report.json").exists())


if __name__ == "__main__":
    unittest.main()
