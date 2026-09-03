from __future__ import annotations

import json
from pathlib import Path

from services.boss_inferred_mechanic_review import audit_inferred_boss_mechanics


def test_audit_collects_only_inferred_mechanics(tmp_path: Path) -> None:
    (tmp_path / "boss.json").write_text(
        json.dumps(
            {
                "id": "boss",
                "name": "Boss",
                "content_id": "trial",
                "source": {"url": "https://example.test/boss", "revision_id": 12},
                "mechanics": [
                    {
                        "name": "Hazard",
                        "description": "Move out.",
                        "mechanic_type": "area_attack",
                        "damage_type": "flame",
                        "requires_movement": True,
                        "interpretation_status": "inferred",
                    },
                    {
                        "name": "Reviewed",
                        "description": "Reviewed row.",
                        "mechanic_type": "targeted_hazard",
                        "interpretation_status": "curated",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    audit = audit_inferred_boss_mechanics(tmp_path)
    assert audit.source_files == 1
    assert audit.bosses_with_inferred_mechanics == 1
    assert len(audit.rows) == 1
    assert audit.rows[0].mechanic_name == "Hazard"
    assert audit.rows[0].requires_movement is True
    assert audit.issue_rows == ()


def test_audit_flags_missing_review_fields(tmp_path: Path) -> None:
    (tmp_path / "boss.json").write_text(
        json.dumps(
            {
                "id": "boss",
                "name": "Boss",
                "mechanics": [
                    {
                        "name": "",
                        "description": "",
                        "mechanic_type": "",
                        "interpretation_status": "inferred",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    audit = audit_inferred_boss_mechanics(tmp_path)
    assert len(audit.issue_rows) == 1
    assert set(audit.issue_rows[0].issues) == {
        "missing_name",
        "missing_mechanic_type",
        "missing_description",
    }
