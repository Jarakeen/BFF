from __future__ import annotations

import json
import sqlite3

from services.esologs_combat_importer import EsoLogsCombatImporter
from services.esologs_player_details_import_service import (
    EsoLogsPlayerDetailsImportService,
    normalize_player_details,
)


def _actor(actor_id: int, name: str, *, role: str | None = None) -> dict:
    row = {
        "id": actor_id,
        "name": name,
        "displayName": name,
        "type": "Dragonknight",
        "anonymous": False,
    }
    if role is not None:
        row["role"] = role
    return row


def test_normalize_grouped_player_details() -> None:
    rows = normalize_player_details(
        {
            "healers": [_actor(1, "Heal")],
            "tanks": [_actor(2, "Tank")],
            "dps": [_actor(3, "Damage")],
        }
    )

    assert [(row.role, row.actor["id"]) for row in rows] == [
        ("healer", 1),
        ("tank", 2),
        ("dps", 3),
    ]


def test_normalize_wrapped_json_scalar_player_details() -> None:
    payload = {
        "data": {
            "playerDetails": {
                "tanks": {
                    "a": _actor(5, "Dualtalons"),
                    "b": _actor(1, "Fulcinator"),
                }
            }
        }
    }
    rows = normalize_player_details(json.dumps(payload))

    assert {(row.role, row.actor["id"]) for row in rows} == {
        ("tank", 1),
        ("tank", 5),
    }


def test_normalize_flat_player_list_roles() -> None:
    rows = normalize_player_details(
        [
            _actor(1, "Fulcinator", role="Tank"),
            {**_actor(2, "Healer"), "roleName": "Healing"},
            {**_actor(3, "Damage"), "specRole": "DD"},
        ]
    )

    assert [(row.role, row.actor["id"]) for row in rows] == [
        ("tank", 1),
        ("healer", 2),
        ("dps", 3),
    ]


def test_import_service_persists_normalized_roles() -> None:
    db = sqlite3.connect(":memory:")
    EsoLogsCombatImporter(db, client=None)  # type: ignore[arg-type]

    def query(_query: str, _variables: dict) -> dict:
        return {
            "reportData": {
                "report": {
                    "playerDetails": [
                        _actor(1, "Fulcinator", role="Tank"),
                        _actor(5, "Dualtalons", role="Tank"),
                    ]
                }
            }
        }

    imported = EsoLogsPlayerDetailsImportService(db, query).import_fight(
        report_code="REPORT",
        fight={"id": 30, "startTime": 1000.0, "endTime": 2000.0},
    )

    assert imported == 2
    rows = db.execute(
        "SELECT actor_id, name, role FROM log_actor ORDER BY actor_id"
    ).fetchall()
    assert [(int(row[0]), str(row[1]), str(row[2])) for row in rows] == [
        (1, "Fulcinator", "tank"),
        (5, "Dualtalons", "tank"),
    ]
