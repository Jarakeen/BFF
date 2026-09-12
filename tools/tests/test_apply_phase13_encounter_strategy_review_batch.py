from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.apply_phase13_encounter_strategy_review_batch import apply_review_batch


def _packet(tmp_path: Path) -> Path:
    path = tmp_path / "packet.json"
    path.write_text(
        json.dumps(
            {
                "candidate_hostile_families": [
                    {
                        "ability_game_id": 166019,
                        "canonical_mechanic_id": None,
                        "review_status": "pending",
                        "review_rationale": "",
                    },
                    {
                        "ability_game_id": 166020,
                        "canonical_mechanic_id": None,
                        "review_status": "pending",
                        "review_rationale": "",
                    },
                ],
                "review_state": {
                    "canonical_strategy_changed": False,
                    "canonical_mechanics_changed": False,
                    "pending_human_review": True,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _batch(tmp_path: Path, decisions: list[dict]) -> Path:
    path = tmp_path / "batch.json"
    path.write_text(json.dumps({"decisions": decisions}), encoding="utf-8")
    return path


def test_apply_review_batch_accepts_and_rejects_without_canonical_promotion(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    batch = _batch(
        tmp_path,
        [
            {
                "ability_game_id": 166019,
                "status": "accepted",
                "canonical_mechanic_id": "acid_reflux",
                "rationale": "Reviewed repeated event shape against encounter evidence.",
            },
            {
                "ability_game_id": 166020,
                "status": "rejected",
                "rationale": "Observed family does not match the reviewed mechanic shape.",
            },
        ],
    )

    changed, preserved = apply_review_batch(packet_path=packet, batch_path=batch)
    payload = json.loads(packet.read_text(encoding="utf-8"))

    assert (changed, preserved) == (2, 0)
    accepted, rejected = payload["candidate_hostile_families"]
    assert accepted["review_status"] == "accepted"
    assert accepted["canonical_mechanic_id"] == "acid_reflux"
    assert rejected["review_status"] == "rejected"
    assert rejected["canonical_mechanic_id"] is None
    assert payload["review_state"] == {
        "canonical_strategy_changed": False,
        "canonical_mechanics_changed": False,
        "pending_human_review": False,
    }


def test_apply_review_batch_preserves_existing_human_decision(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["candidate_hostile_families"][0].update(
        review_status="accepted",
        canonical_mechanic_id="existing_mechanic",
        review_rationale="Already reviewed.",
    )
    packet.write_text(json.dumps(payload), encoding="utf-8")
    batch = _batch(
        tmp_path,
        [
            {
                "ability_game_id": 166019,
                "status": "rejected",
                "rationale": "Must not overwrite prior review.",
            }
        ],
    )

    changed, preserved = apply_review_batch(packet_path=packet, batch_path=batch)
    result = json.loads(packet.read_text(encoding="utf-8"))["candidate_hostile_families"][0]

    assert (changed, preserved) == (0, 1)
    assert result["review_status"] == "accepted"
    assert result["canonical_mechanic_id"] == "existing_mechanic"


@pytest.mark.parametrize(
    "decision",
    [
        {"ability_game_id": 166019, "status": "accepted", "rationale": "missing id"},
        {
            "ability_game_id": 166019,
            "status": "accepted",
            "canonical_mechanic_id": "Acid Reflux",
            "rationale": "bad canonical id",
        },
        {
            "ability_game_id": 166019,
            "status": "rejected",
            "canonical_mechanic_id": "acid_reflux",
            "rationale": "rejected cannot bind",
        },
        {"ability_game_id": 166019, "status": "accepted", "canonical_mechanic_id": "acid_reflux", "rationale": ""},
    ],
)
def test_apply_review_batch_fails_closed_on_invalid_review(tmp_path: Path, decision: dict) -> None:
    with pytest.raises(ValueError):
        apply_review_batch(packet_path=_packet(tmp_path), batch_path=_batch(tmp_path, [decision]))
