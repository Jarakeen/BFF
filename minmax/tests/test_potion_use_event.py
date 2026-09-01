from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from minmax.combat_effect_semantics import GameUpdate
from minmax.potion_use_event import PotionUseEventResolver


def _write_processed(path: Path) -> None:
    formula = {
        "ingredients": ["Corn Flower", "Lady's Smock", "Water Hyacinth"],
        "effects": ["Restore Magicka", "Increase Spell Power", "Spell Critical"],
    }
    payload = {
        "effects": [
            {
                "effect_name": "Restore Magicka",
                "formulas": [formula],
                "potion_tiers": [
                    {"solvent": "Lorkhan's Tears", "level": "150", "name": "Essence of Magicka", "values": ["7582", "36.6", "40.6"]}
                ],
            },
            {
                "effect_name": "Increase Spell Power",
                "formulas": [formula],
                "potion_tiers": [
                    {"solvent": "Lorkhan's Tears", "level": "150", "name": "Essence of Spell Power", "values": ["36.6", "40.6"]}
                ],
            },
            {
                "effect_name": "Spell Critical",
                "formulas": [formula],
                "potion_tiers": [
                    {"solvent": "Lorkhan's Tears", "level": "150", "name": "Essence of Spell Critical", "values": ["36.6", "40.6"]}
                ],
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE effect (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT);
            CREATE TABLE effect_variant (id INTEGER PRIMARY KEY, effect_id INTEGER NOT NULL, type TEXT);
            """
        )
        for effect_id, name in enumerate(("Restore Magicka", "Increase Spell Power", "Spell Critical"), start=1):
            db.execute("INSERT INTO effect(id, name, category) VALUES (?, ?, 'alchemy')", (effect_id, name))
            db.execute("INSERT INTO effect_variant(id, effect_id, type) VALUES (?, ?, 'Potion')", (100 + effect_id, effect_id))


def test_spell_power_use_separates_instant_restore_and_timed_traits(tmp_path: Path):
    processed = tmp_path / "alchemy_effects.json"
    database = tmp_path / "eso.db"
    _write_processed(processed)
    _write_db(database)

    event = PotionUseEventResolver(database_path=database, processed_path=processed).resolve("spell power")

    assert event.resolved
    assert len(event.formula_ids) == 1
    assert [(value.trait, value.magnitude) for value in event.instant_restores] == [("Restore Magicka", 7582.0)]
    assert {value.trait for value in event.timed_traits} == {"Increase Spell Power", "Spell Critical"}
    assert all(value.duration == 36.6 for value in event.timed_traits)
    assert all(value.triple_duration == 40.6 for value in event.timed_traits)


def test_spell_power_use_exposes_all_three_named_buff_grants(tmp_path: Path):
    processed = tmp_path / "alchemy_effects.json"
    database = tmp_path / "eso.db"
    _write_processed(processed)
    _write_db(database)

    event = PotionUseEventResolver(database_path=database, processed_path=processed).resolve("spell power")

    assert {(grant.source_trait, grant.buff_name) for grant in event.buff_grants} == {
        ("Restore Magicka", "Major Intellect"),
        ("Increase Spell Power", "Major Sorcery"),
        ("Spell Critical", "Major Prophecy"),
    }
    assert all(grant.duration == 36.6 for grant in event.buff_grants)
    assert all(grant.triple_duration == 40.6 for grant in event.buff_grants)


def test_restore_duration_is_not_misapplied_as_a_timed_restore(tmp_path: Path):
    processed = tmp_path / "alchemy_effects.json"
    database = tmp_path / "eso.db"
    _write_processed(processed)
    _write_db(database)

    event = PotionUseEventResolver(database_path=database, processed_path=processed).resolve("spell power")
    restore = event.instant_restores[0]

    assert restore.kind == "instant_restore"
    assert restore.duration is None
    assert restore.triple_duration == 40.6
    assert next(grant for grant in event.buff_grants if grant.source_trait == "Restore Magicka").duration == 36.6


def test_u51_temporal_values_fail_closed_until_u51_tier_source_exists(tmp_path: Path):
    processed = tmp_path / "alchemy_effects.json"
    database = tmp_path / "eso.db"
    _write_processed(processed)
    _write_db(database)

    event = PotionUseEventResolver(
        database_path=database,
        processed_path=processed,
        game_update=GameUpdate.U51,
    ).resolve("spell power")

    assert not event.resolved
    assert "not sourced for U51" in event.unresolved[0]
