from __future__ import annotations

import json
from pathlib import Path

from tools.build_phase13_encounter_strategy_review_packet import build_review_packet


def _corpus(tmp_path: Path) -> Path:
    path = tmp_path / "reef_guardian_corpus.json"
    player_details = {
        "tanks": [{"id": 1, "name": "Tank"}],
        "healers": [{"id": 2, "name": "Healer"}],
        "dps": [{"id": 3, "name": "DD"}],
    }

    def fight(fight_id: int, *, kill: bool):
        base = fight_id * 100000
        return {
            "metadata": {
                "id": fight_id,
                "name": "Reef Guardian",
                "kill": kill,
                "difficulty": 2,
                "startTime": base,
                "endTime": base + 20000,
            },
            "player_details": player_details,
            "events": [
                {
                    "type": "damage",
                    "timestamp": base + 1000,
                    "sourceID": 3,
                    "sourceIsFriendly": True,
                    "targetID": 900,
                    "targetIsFriendly": False,
                    "abilityGameID": 10,
                    "amount": 1000,
                },
                {
                    "type": "begincast",
                    "timestamp": base + 2000,
                    "sourceID": 900,
                    "sourceIsFriendly": False,
                    "abilityGameID": 166019,
                },
                {
                    "type": "cast",
                    "timestamp": base + 2500,
                    "sourceID": 900,
                    "sourceIsFriendly": False,
                    "abilityGameID": 166019,
                },
                {
                    "type": "damage",
                    "timestamp": base + 3000,
                    "sourceID": 900,
                    "sourceIsFriendly": False,
                    "targetID": 1,
                    "targetIsFriendly": True,
                    "abilityGameID": 166019,
                    "amount": 5000,
                },
                {
                    "type": "heal",
                    "timestamp": base + 3100,
                    "sourceID": 2,
                    "sourceIsFriendly": True,
                    "targetID": 1,
                    "targetIsFriendly": True,
                    "abilityGameID": 20,
                    "amount": 4000,
                },
            ],
        }

    payload = {
        "schema_version": 1,
        "encounter": "reef guardian",
        "reports": {
            "DSR": {
                "matching_fight_count": 2,
                "fights": {"7": fight(7, kill=True), "8": fight(8, kill=False)},
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_review_packet_stays_observational_and_pending(tmp_path: Path) -> None:
    packet = build_review_packet(path=_corpus(tmp_path), bin_seconds=10.0, signature_limit=20)

    assert packet["evidence_status"] == "candidate_observational_only"
    assert packet["fight_count"] == 2
    assert packet["kill_count"] == 1
    assert packet["wipe_count"] == 1
    assert packet["review_state"] == {
        "canonical_strategy_changed": False,
        "canonical_mechanics_changed": False,
        "pending_human_review": True,
    }

    family = next(row for row in packet["candidate_hostile_families"] if row["ability_game_id"] == 166019)
    assert family["fight_count"] == 2
    assert family["canonical_mechanic_id"] is None
    assert family["review_status"] == "pending"
    assert family["review_rationale"] == ""
    assert {row["event_type"] for row in family["event_shapes"]} == {"begincast", "cast", "damage"}


def test_review_packet_includes_role_pressure_without_strategy_inference(tmp_path: Path) -> None:
    packet = build_review_packet(path=_corpus(tmp_path), bin_seconds=10.0, signature_limit=20)
    first = packet["fights"][0]

    assert first["role_counts"] == {"tank": 1, "healer": 1, "dps": 1}
    assert first["observed_primary_target_id"] == 900
    pressure = first["pressure_windows"][0]
    assert pressure["primary_target_damage"] == 1000.0
    assert pressure["incoming_player_damage"] == 5000.0
    assert pressure["healer_output"] == 4000.0
    assert all("strategy" not in family for family in packet["candidate_hostile_families"])


def test_review_packet_rejects_invalid_analysis_controls(tmp_path: Path) -> None:
    path = _corpus(tmp_path)

    for kwargs in ({"bin_seconds": 0.0}, {"signature_limit": 0}):
        try:
            build_review_packet(path=path, **kwargs)
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError("invalid review control should fail closed")
