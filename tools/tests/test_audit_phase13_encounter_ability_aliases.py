from __future__ import annotations

import json
from pathlib import Path

from tools.audit_phase13_encounter_ability_aliases import (
    discover_aliases,
    discover_hostile_signatures,
)


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
                            {
                                "type": "applydebuff",
                                "timestamp": 1700,
                                "sourceID": 900,
                                "sourceIsFriendly": False,
                                "targetID": 11,
                                "targetIsFriendly": True,
                                "abilityGameID": 444,
                                "ability": {"name": "Corrosive Mark"},
                            },
                            {
                                "type": "heal",
                                "timestamp": 1800,
                                "sourceID": 900,
                                "sourceIsFriendly": False,
                                "targetID": 900,
                                "targetIsFriendly": False,
                                "abilityGameID": 555,
                                "ability": {"name": "Hostile Self Heal"},
                            },
                        ],
                    },
                    "8": {
                        "metadata": {"id": 8, "name": "Reef Guardian"},
                        "events": [
                            {
                                "type": "cast",
                                "timestamp": 2000,
                                "sourceID": 901,
                                "sourceIsFriendly": False,
                                "abilityGameID": 111,
                                "ability": {"name": "Acid Reflux"},
                            },
                            {
                                "type": "damage",
                                "timestamp": 2500,
                                "sourceID": 901,
                                "sourceIsFriendly": False,
                                "targetID": 12,
                                "targetIsFriendly": True,
                                "abilityGameID": 222,
                                "ability": {"name": "Acid Reflux"},
                                "tick": True,
                            },
                            {
                                "type": "damage",
                                "timestamp": 2600,
                                "sourceID": 901,
                                "sourceIsFriendly": False,
                                "targetID": 13,
                                "targetIsFriendly": True,
                                "abilityGameID": 222,
                                "ability": {"name": "Acid Reflux"},
                                "tick": True,
                            },
                        ],
                    },
                }
            }
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_discover_aliases_reports_hostile_name_id_event_shapes(tmp_path: Path) -> None:
    rows = discover_aliases(path=_corpus(tmp_path), query_terms=("acid",))

    assert rows == (
        ("Acid Reflux", 222, "damage", True, 3),
        ("Acid Reflux", 111, "cast", None, 2),
    )


def test_discover_aliases_can_include_friendly_sources(tmp_path: Path) -> None:
    rows = discover_aliases(
        path=_corpus(tmp_path),
        query_terms=("spray",),
        hostile_only=False,
    )

    assert rows == (("Acid Spray", 333, "damage", None, 1),)


def test_discover_hostile_signatures_ranks_cross_fight_repetition_before_raw_count(tmp_path: Path) -> None:
    rows = discover_hostile_signatures(path=_corpus(tmp_path))

    assert rows[:3] == (
        ("Acid Reflux", 222, "damage", True, 3, 2),
        ("Acid Reflux", 111, "cast", None, 2, 2),
        ("Corrosive Mark", 444, "applydebuff", None, 1, 1),
    )
    assert all(name != "Hostile Self Heal" for name, *_rest in rows)


def test_discover_hostile_signatures_excludes_friendly_source_rows(tmp_path: Path) -> None:
    rows = discover_hostile_signatures(path=_corpus(tmp_path))

    assert all(ability_id != 333 for _name, ability_id, *_rest in rows)
