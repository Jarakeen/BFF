from __future__ import annotations

import sqlite3
from pathlib import Path

from minmax.build_backed_roster_lab import BuildBackedRosterLab
from minmax.character_build.character_class import CharacterClass
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.role import Role


SPELL_POWER_CURE_ID = 1001
CORPSEBURSTER_ID = 1002
ALKOSH_ID = 1003


def _db(path: Path) -> Path:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE gear_set (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT, max_equip_count INTEGER)"
        )
        connection.execute(
            "CREATE TABLE gear_set_bonus (id INTEGER PRIMARY KEY, set_id INTEGER NOT NULL, piece_count INTEGER NOT NULL, description TEXT, UNIQUE(set_id, piece_count))"
        )
        sets = [
            (SPELL_POWER_CURE_ID, "Spell Power Cure"),
            (CORPSEBURSTER_ID, "Corpseburster"),
            (ALKOSH_ID, "Roar of Alkosh"),
        ]
        connection.executemany(
            "INSERT INTO gear_set (id, name, category, max_equip_count) VALUES (?, ?, 'test', 5)",
            sets,
        )
        connection.executemany(
            "INSERT INTO gear_set_bonus (id, set_id, piece_count, description) VALUES (?, ?, 5, 'verified test bonus')",
            [(2001, SPELL_POWER_CURE_ID), (2002, CORPSEBURSTER_ID), (2003, ALKOSH_ID)],
        )
        connection.commit()
    finally:
        connection.close()
    return path


def test_verified_set_name_mappings_resolve(tmp_path: Path) -> None:
    resolver = GearSetEffectVariantResolver(GearSetRepository(_db(tmp_path / "sets.db")))

    assert resolver.resolve(SPELL_POWER_CURE_ID, 5)[0].name == "major_courage"
    assert resolver.resolve(CORPSEBURSTER_ID, 5)[0].name == "minor_breach"
    assert resolver.resolve(ALKOSH_ID, 5)[0].name == "roar_of_alkosh"


def test_multi_set_build_produces_both_support_effects(tmp_path: Path) -> None:
    lab = BuildBackedRosterLab(_db(tmp_path / "sets.db"))

    player = lab.add_player(
        "Healer 01",
        Role.HEALER,
        CharacterClass.WARDEN,
        gear_sets=((SPELL_POWER_CURE_ID, 5), (ALKOSH_ID, 5)),
    )

    assert player.validation_errors == ()
    assert "major_courage" in player.resolved_effects
    assert "roar_of_alkosh" in player.resolved_effects


def test_roster_capabilities_use_the_same_gear_aware_resolver(tmp_path: Path) -> None:
    lab = BuildBackedRosterLab(_db(tmp_path / "sets.db"))

    lab.add_player(
        "Healer 01",
        Role.HEALER,
        CharacterClass.WARDEN,
        gear_sets=((SPELL_POWER_CURE_ID, 5),),
    )

    capabilities = lab.capabilities()

    assert "major_courage" in capabilities
    assert capabilities["major_courage"][0].character_name == "Healer 01"
