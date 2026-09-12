from __future__ import annotations

import json
from pathlib import Path

from tools.audit_phase13_encounter_ability_aliases import discover_aliases


def _corpus(tmp_path: Path) -> Path:
    path = tmp_path / "reef_guardian_corpus.json"
    payload = {
        "reports": {
            "DSR": {
                "fights": {
                    "7": {
                        "metadata": {"id": 7, "name": "Reef Guardian"},
                        "events": [
                            {
                                "type": "cast",
                                "timestamp": 1000,
                                "sourceID": 900,
                                "sourceIsFriendly": False,
                                "abilityGameID": 111,
                                "ability": {"name": "Acid Reflux"},
                            },
                            {
                                "type": "damage",
                                "timestamp": 1500,
                                "sourceID": 900,
                                "sourceIsFriendly": False,
                                "targetID": 11,
                                "targetIsFriendly": True,
                                "abilityGameID": 222,
                                "ability": {"name": "Acid Reflux"},
                                "tick": True,
                            },
                            {
                                "type": "damage",
                                "timestamp": 1600,
                                "sourceID": 11,
                                "sourceIsFriendly": True,
                                "targetID": 900,
                                "targetIsFriendly": False,
                                "abilityGameID": 333,
                                "ability": {"name": "Acid Spray"},
                            },
                        ],
                    }
                }
            }
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_discover_aliases_reports_hostile_name_id_event_shapes(tmp_path: Path) -> None:
    rows = discover_aliases(path=_corpus(tmp_path), query_terms=("acid",))

    assert rows == (
        ("Acid Reflux", 111, "cast", None, 1),
        ("Acid Reflux", 222, "damage", True, 1),
    )


def test_discover_aliases_can_include_friendly_sources(tmp_path: Path) -> None:
    rows = discover_aliases(
        path=_corpus(tmp_path),
        query_terms=("spray",),
        hostile_only=False,
    )

    assert rows == (("Acid Spray", 333, "damage", None, 1),)
