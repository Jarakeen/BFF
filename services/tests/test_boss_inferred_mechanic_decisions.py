from __future__ import annotations

import json
from pathlib import Path

from services.boss_inferred_mechanic_decisions import (
    ACCEPTED,
    PENDING,
    InferredMechanicDecision,
    audit_decisions,
    build_pending_decision_manifest,
    load_decisions,
)


def _write_boss(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "id": "oaxiltso",
                "name": "Oaxiltso",
                "mechanics": [
                    {
                        "name": "Noxious Sludge",
                        "description": "Poisons two targets until they cleanse.",
                        "mechanic_type": "targeted_hazard",
                        "target_count": 2,
                        "requires_cleanse": True,
                        "interpretation_status": "inferred",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_pending_manifest_covers_current_queue(tmp_path: Path) -> None:
    _write_boss(tmp_path / "oaxiltso.json")

    payload = build_pending_decision_manifest(tmp_path)

    assert payload["schema_version"] == 1
    assert payload["decisions"] == [
        {
            "encounter_id": "oaxiltso",
            "mechanic_name": "Noxious Sludge",
            "status": PENDING,
            "rationale": "",
        }
    ]


def test_decision_audit_requires_complete_keys_and_rationale(tmp_path: Path) -> None:
    _write_boss(tmp_path / "oaxiltso.json")

    accepted = InferredMechanicDecision(
        encounter_id="oaxiltso",
        mechanic_name="Noxious Sludge",
        status=ACCEPTED,
        rationale="Source text explicitly says two targets remain poisoned until cleansing.",
    )
    clean = audit_decisions(tmp_path, [accepted])
    assert clean.blocked is False
    assert clean.expected_count == 1

    missing_rationale = audit_decisions(
        tmp_path,
        [
            InferredMechanicDecision(
                encounter_id="oaxiltso",
                mechanic_name="Noxious Sludge",
                status=ACCEPTED,
                rationale="",
            )
        ],
    )
    assert missing_rationale.blocked is True
    assert missing_rationale.accepted_without_rationale == (("oaxiltso", "Noxious Sludge"),)


def test_load_decisions_normalizes_status(tmp_path: Path) -> None:
    manifest = tmp_path / "review.json"
    manifest.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "encounter_id": "oaxiltso",
                        "mechanic_name": "Noxious Sludge",
                        "status": "ACCEPTED",
                        "rationale": "Reviewed.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    rows = load_decisions(manifest)
    assert rows[0].status == ACCEPTED
