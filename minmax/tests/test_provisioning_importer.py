from __future__ import annotations

import json
import sqlite3

from importers.provisioning_importer import UespProvisioningImporter
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE entity (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                slug TEXT NOT NULL,
                UNIQUE (entity_type, slug)
            );
            CREATE TABLE entity_source (
                id INTEGER PRIMARY KEY,
                entity_id TEXT NOT NULL,
                source TEXT NOT NULL,
                source_entity_type TEXT,
                source_id TEXT,
                source_name TEXT,
                raw_json TEXT,
                UNIQUE (entity_id, source, source_entity_type, source_id)
            );
            """
        )
    return path


def _export(path, records):
    path.write_text(
        json.dumps(
            {"numRecords": len(records), "minedItemSummary": records}
        ),
        encoding="utf-8",
    )
    return path


def test_imports_canonical_food_drink_entities_and_numeric_crosswalks(tmp_path):
    database = _database(tmp_path)
    food = _export(
        tmp_path / "food.json",
        [
            {
                "itemId": "133556",
                "name": "Clockwork Citrus Filet",
                "type": "4",
                "abilityDesc": (
                    "Increase Max Health by |cffffff3326|r, Health Recovery by "
                    "|cffffff406|r, Max Magicka by |cffffff3080|r and Magicka "
                    "Recovery by |cffffff338|r for |cffffff2|r hours."
                ),
            },
            {
                "itemId": "200",
                "name": "Duplicate Meal",
                "type": "4",
                "abilityDesc": "Increase Max Health by 1000 for 1 hour.",
            },
            {
                "itemId": "201",
                "name": "Duplicate Meal",
                "type": "4",
                "abilityDesc": "Increase Max Health by 1200 for 1 hour.",
            },
        ],
    )
    drink = _export(
        tmp_path / "drink.json",
        [
            {
                "itemId": "300",
                "name": "Test Tonic",
                "type": "12",
                "abilityDesc": "Increase Magicka Recovery by 300 for 1 hour.",
            }
        ],
    )

    summary = UespProvisioningImporter(database).run(
        food_path=food,
        drink_path=drink,
    )

    assert summary.source_records == 4
    assert summary.entities_created == 3
    assert summary.mappings_inserted == 4
    assert summary.unresolved == ()
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM entity WHERE entity_type='food'"
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM entity WHERE entity_type='drink'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM entity_source WHERE entity_id='food_duplicate_meal'"
        ).fetchone()[0] == 2

    effects, unresolved = ProvisioningStaticRepository(database).resolve(
        "clockwork citrus"
    )
    assert unresolved == []
    assert {effect.stat: effect.value for effect in effects} == {
        StatId.MAX_HEALTH: 3326.0,
        StatId.MAX_MAGICKA: 3080.0,
        StatId.HEALTH_RECOVERY: 406.0,
        StatId.MAGICKA_RECOVERY: 338.0,
    }


def test_import_is_idempotent(tmp_path):
    database = _database(tmp_path)
    food = _export(
        tmp_path / "food.json",
        [{"itemId": "1", "name": "Meal", "type": "4", "abilityDesc": "Increase Max Health by 1."}],
    )
    drink = _export(
        tmp_path / "drink.json",
        [{"itemId": "2", "name": "Drink", "type": "12", "abilityDesc": "Increase Magicka Recovery by 1."}],
    )
    importer = UespProvisioningImporter(database)

    importer.run(food_path=food, drink_path=drink)
    second = importer.run(food_path=food, drink_path=drink)

    assert second.entities_created == 0
    assert second.entities_existing == 2
    assert second.mappings_inserted == 0
    assert second.mappings_updated == 2
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM entity_source").fetchone()[0] == 2
