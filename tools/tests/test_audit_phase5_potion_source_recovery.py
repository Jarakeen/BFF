from __future__ import annotations

import json
import sqlite3

from tools.audit_phase5_potion_source_recovery import (
    _db_effect_status,
    _processed_inventory,
)


def test_processed_inventory_reads_effect_records(tmp_path):
    path = tmp_path / "alchemy_effects.json"
    path.write_text(
        json.dumps(
            {
                "effects": [
                    {
                        "effect_name": "Restore Magicka",
                        "potion_tiers": [{"name": "Essence"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    inventory = _processed_inventory(path)

    assert "restore magicka" in inventory
    assert inventory["restore magicka"]["effect_name"] == "Restore Magicka"


def test_db_effect_status_counts_potion_variants_and_sources(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE effect (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE effect_variant (
                id INTEGER PRIMARY KEY,
                effect_id INTEGER NOT NULL,
                type TEXT
            );
            CREATE TABLE effect_source (
                id INTEGER PRIMARY KEY,
                effect_variant_id INTEGER NOT NULL
            );
            INSERT INTO effect(id, name) VALUES (1, 'Increase Spell Power');
            INSERT INTO effect_variant(id, effect_id, type) VALUES (10, 1, 'Potion');
            INSERT INTO effect_source(id, effect_variant_id) VALUES (20, 10);
            """
        )

        assert _db_effect_status(db, "Increase Spell Power") == (1, 1, 1)
        assert _db_effect_status(db, "Restore Magicka") == (0, 0, 0)
