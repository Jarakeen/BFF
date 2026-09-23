from __future__ import annotations

from pathlib import Path

from services.build_catalog_service import BuildCatalogService


def _catalog() -> dict:
    return {
        "schema_version": 4,
        "players": [{"player_id": "p1", "gamertag": "Rikbacon"}],
        "characters": [
            {
                "character_id": "c1",
                "player_id": "p1",
                "name": "Tanky",
                "gamertag": "Rikbacon",
                "eso_class": "Dragonknight",
            }
        ],
        "builds": [
            {
                "build_id": "b1",
                "character_id": "c1",
                "name": "Main Tank",
                "payload": {
                    "Name": "Tanky",
                    "Gamertag": "Rikbacon",
                    "BuildName": "Main Tank",
                    "Armor": {"Chest": {"Set": "Pearlescent Ward"}},
                },
            }
        ],
        "team_assignments": [],
    }


def test_build_catalog_round_trips_through_sqlite(tmp_path: Path) -> None:
    database = tmp_path / "foundrydock.db"
    service = BuildCatalogService(database)

    service.save(_catalog())

    restored = service.load_strict()
    assert [row["player_id"] for row in restored["players"]] == ["p1"]
    assert [row["character_id"] for row in restored["characters"]] == ["c1"]
    assert [row["build_id"] for row in restored["builds"]] == ["b1"]


def test_build_catalog_sqlite_save_replaces_singleton_payload(tmp_path: Path) -> None:
    database = tmp_path / "foundrydock.db"
    service = BuildCatalogService(database)
    first = _catalog()
    service.save(first)

    revised = _catalog()
    revised["builds"][0]["name"] = "Revised Tank"
    service.save(revised)

    restored = service.load_strict()
    assert len(restored["builds"]) == 1
    assert restored["builds"][0]["name"] == "Revised Tank"
