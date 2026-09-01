from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from minmax.character_build.effect_layer import EffectLayer
from minmax.combat_effect_semantics import GameUpdate
from minmax.potion_availability_repository import PotionAvailabilityRepository


def _write_processed(path: Path) -> None:
    formulas = [
        {
            "ingredients": ["Corn Flower", "Lady's Smock", "Namira's Rot"],
            "effects": ["Restore Magicka", "Increase Spell Power", "Spell Critical"],
        },
        {
            "ingredients": ["Corn Flower", "Lady's Smock", "Water Hyacinth"],
            "effects": ["Restore Magicka", "Increase Spell Power", "Spell Critical"],
        },
    ]
    payload = {
        "effects": [
            {
                "effect_name": "Restore Magicka",
                "source_files": ["restore_magicka.html"],
                "formulas": formulas,
            },
            {
                "effect_name": "Increase Spell Power",
                "source_files": ["increase_spell_power.html"],
                "formulas": formulas,
            },
            {
                "effect_name": "Spell Critical",
                "source_files": ["spell_critical.html"],
                "formulas": formulas,
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_db(path: Path, *, omit: str | None = None) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE effect (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT
            );
            CREATE TABLE effect_variant (
                id INTEGER PRIMARY KEY,
                effect_id INTEGER NOT NULL,
                type TEXT,
                description TEXT,
                icon TEXT,
                raw_json TEXT
            );
            """
        )
        rows = (
            (1, "Restore Magicka", "alchemy"),
            (2, "Increase Spell Power", "alchemy"),
            (3, "Spell Critical", "alchemy"),
        )
        for effect_id, name, category in rows:
            db.execute("INSERT INTO effect(id, name, category) VALUES (?, ?, ?)", (effect_id, name, category))
            if name != omit:
                db.execute(
                    "INSERT INTO effect_variant(id, effect_id, type) VALUES (?, ?, 'Potion')",
                    (100 + effect_id, effect_id),
                )


def test_legacy_spell_power_alias_resolves_effect_family_with_two_equivalent_formulas(tmp_path: Path):
    processed = tmp_path / "alchemy_effects.json"
    database = tmp_path / "eso.db"
    _write_processed(processed)
    _write_db(database)

    result = PotionAvailabilityRepository(database, processed).resolve("spell power")

    assert result.resolved
    assert len(result.formulas) == 2
    assert set(result.canonical_traits) == {
        "Restore Magicka",
        "Increase Spell Power",
        "Spell Critical",
    }
    assert {effect.name for effect in result.effects} == {
        "restore_magicka",
        "increase_spell_power",
        "spell_critical",
    }
    assert all(effect.layer is EffectLayer.CONSUMABLE for effect in result.effects)
    assert all(effect.trigger == "potion_use" for effect in result.effects)
    assert all("uptime are not assumed" in str(effect.condition) for effect in result.effects)


def test_exact_formula_id_resolves_one_recipe(tmp_path: Path):
    processed = tmp_path / "alchemy_effects.json"
    database = tmp_path / "eso.db"
    _write_processed(processed)
    _write_db(database)
    repository = PotionAvailabilityRepository(database, processed)

    family = repository.resolve("spell power")
    formula_id = family.formulas[0].canonical_id
    exact = repository.resolve(formula_id)

    assert exact.resolved
    assert len(exact.formulas) == 1
    assert exact.formulas[0].canonical_id == formula_id
    assert set(effect.name for effect in exact.effects) == {
        "restore_magicka",
        "increase_spell_power",
        "spell_critical",
    }


def test_unknown_or_ambiguous_human_label_fails_closed(tmp_path: Path):
    processed = tmp_path / "alchemy_effects.json"
    database = tmp_path / "eso.db"
    _write_processed(processed)
    _write_db(database)

    result = PotionAvailabilityRepository(database, processed).resolve("Spell Critical")

    assert not result.resolved
    assert result.effects == ()
    assert "not an exact canonical formula or known legacy alias" in result.unresolved[0]


def test_missing_potion_effect_variant_is_explicitly_unresolved(tmp_path: Path):
    processed = tmp_path / "alchemy_effects.json"
    database = tmp_path / "eso.db"
    _write_processed(processed)
    _write_db(database, omit="Spell Critical")

    result = PotionAvailabilityRepository(database, processed).resolve("spell power")

    assert not result.resolved
    assert {effect.name for effect in result.effects} == {"restore_magicka", "increase_spell_power"}
    assert result.unresolved == ("Potion EffectVariant missing from database: Spell Critical",)


def test_u51_legacy_alias_uses_consolidated_trait_names_and_fails_closed_against_u50_db(tmp_path: Path):
    processed = tmp_path / "alchemy_effects.json"
    database = tmp_path / "eso.db"
    _write_processed(processed)
    _write_db(database)

    result = PotionAvailabilityRepository(
        database,
        processed,
        game_update=GameUpdate.U51,
    ).resolve("spell power")

    assert not result.resolved
    assert set(result.canonical_traits) == {"Restore Magicka", "Increase Power", "Critical"}
    assert "Potion EffectVariant missing from database: Increase Power" in result.unresolved
    assert "Potion EffectVariant missing from database: Critical" in result.unresolved
