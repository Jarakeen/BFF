import sqlite3
from pathlib import Path

from services.nonability_effect_provider_reference_service import (
    NonAbilityEffectProviderReferenceService,
    canonical_identity,
)


def _gear_db(path):
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY,
                set_id INTEGER,
                piece_count INTEGER,
                description TEXT
            );
            INSERT INTO gear_set VALUES (332, 'Master Architect', 'Trial', 5);
            INSERT INTO gear_set_bonus VALUES (1493, 332, 5, 'reviewed bonus');
            """
        )


def test_gear_provider_uses_reviewed_known_effect_registry(tmp_path):
    db_path = tmp_path / "gear.db"
    _gear_db(db_path)

    rows = NonAbilityEffectProviderReferenceService(db_path).gear()

    assert len(rows) == 1
    provider = rows[0]
    assert provider.source_kind == "gear_set"
    assert provider.source_key == "gear_set:master_architect"
    assert provider.source_name == "Master Architect"
    assert provider.effect_key == "major_slayer"
    assert provider.piece_count == 5
    assert provider.trigger == "ultimate_activation_in_combat"
    assert "gear_set_known_effects" in provider.evidence


def test_gear_provider_does_not_parse_unknown_bonus_prose(tmp_path):
    db_path = tmp_path / "gear.db"
    with sqlite3.connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (id INTEGER PRIMARY KEY, name TEXT, category TEXT, max_equip_count INTEGER);
            CREATE TABLE gear_set_bonus (id INTEGER PRIMARY KEY, set_id INTEGER, piece_count INTEGER, description TEXT);
            INSERT INTO gear_set VALUES (999, 'Imaginary Courage Set', 'Test', 5);
            INSERT INTO gear_set_bonus VALUES (9999, 999, 5, 'Grants Major Courage because prose says so.');
            """
        )

    assert NonAbilityEffectProviderReferenceService(db_path).gear() == ()


def test_potion_trait_provider_semantics_are_versioned():
    rows = NonAbilityEffectProviderReferenceService(Path("missing.db")).potions()

    spell_power = [row for row in rows if row.source_name == "Increase Spell Power"]
    assert len(spell_power) == 1
    assert spell_power[0].update == "U50"
    assert spell_power[0].effect_key == "major_sorcery"

    consolidated = [row for row in rows if row.source_name == "Increase Power"]
    assert len(consolidated) == 1
    assert consolidated[0].update == "U51"
    assert consolidated[0].effect_key == "major_brutality"


def test_canonical_identity_matches_named_effect_display_names():
    assert canonical_identity("Major Courage") == "major_courage"
    assert canonical_identity("Jorvuld's Guidance") == "jorvuld_s_guidance"
