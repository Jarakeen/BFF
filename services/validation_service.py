# services/validation_service.py
"""Validation helpers for the normalized ESO reference data set."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


class ValidationService:
    """Validate generated JSON files and export a compact report."""

    def __init__(self, data_directory: str | Path) -> None:
        self.data_directory = Path(data_directory)

    def validate_directory(self) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        total_records = 0
        counts: Counter[str] = Counter()
        expected_files = [
            "skills.json",
            "gear_sets.json",
            "foods.json",
            "potions.json",
            "champion_points.json",
            "class_passives.json",
            "status_effects.json",
            "buff.json",
            "debuffs.json",
            "encounters.json",
            "mechanics.json",
            "armor_passives.json",
            "weapon_passives.json",
            "guild_passives.json",
            "races.json",
            "mundus.json",
            "mythics.json",
            "roster.json",
            "capabilities.json",
            "damage_types.json",
            "enemy_types.json",
        ]

        for file_name in expected_files:
            file_path = self.data_directory / file_name
            if not file_path.exists():
                issues.append({"type": "missing_file", "file": file_name, "message": "File not present"})
                continue

            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                issues.append({"type": "invalid_json", "file": file_name, "message": str(error)})
                continue

            if not isinstance(payload, list):
                issues.append({"type": "invalid_payload", "file": file_name, "message": "Expected a list of records"})
                continue

            counts[file_name] = len(payload)
            total_records += len(payload)

            seen_ids: Counter[str] = Counter()
            for index, record in enumerate(payload):
                if not isinstance(record, dict):
                    issues.append({"type": "invalid_record", "file": file_name, "message": f"Entry {index} is not an object"})
                    continue

                record_id = record.get("id")
                if record_id is not None:
                    seen_ids[str(record_id)] += 1
                    if seen_ids[str(record_id)] > 1:
                        issues.append({"type": "duplicate_id", "file": file_name, "record_id": str(record_id), "message": f"Duplicate id {record_id}"})

                name = record.get("name")
                if not isinstance(name, str) or not name.strip():
                    if file_name not in {"damage_types.json", "enemy_types.json"}:
                        issues.append({"type": "missing_name", "file": file_name, "message": f"Entry {index} missing an acceptable name"})

                required_effects = record.get("required_effects")
                if isinstance(required_effects, list):
                    for effect in required_effects:
                        if isinstance(effect, str) and effect.strip():
                            effect_file = self.data_directory / "status_effects.json"
                            if not effect_file.exists():
                                continue
                            try:
                                payload_effects = json.loads(effect_file.read_text(encoding="utf-8"))
                            except (OSError, json.JSONDecodeError):
                                continue
                            effect_names = {entry.get("name") for entry in payload_effects if isinstance(entry, dict)}
                            if effect not in effect_names:
                                issues.append({"type": "invalid_reference", "file": file_name, "reference": effect, "message": f"Missing referenced effect {effect}"})

        summary = {
            "total_files": len(expected_files),
            "present_files": len(counts),
            "total_records": total_records,
            "file_counts": dict(counts),
        }
        report = {
            "is_valid": not issues,
            "summary": summary,
            "issues": issues,
        }
        self.export_report(report)
        return report

    def export_report(self, report: dict[str, Any], output_path: str | None = None) -> Path:
        output = Path(output_path) if output_path is not None else self.data_directory / "validation_report.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return output
