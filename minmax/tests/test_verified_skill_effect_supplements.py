from __future__ import annotations

import sqlite3
from pathlib import Path

from minmax.skill_effect_repository import SkillEffectRepository


def _db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                target TEXT,
                duration REAL,
                base_ability_id INTEGER,
                morph INTEGER
            );
            CREATE TABLE effect (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT
            );
            CREATE TABLE effect_variant (
                id INTEGER PRIMARY KEY,
                effect_id INTEGER NOT NULL,
                type TEXT
            );
            CREATE TABLE effect_source (
                id INTEGER PRIMARY KEY,
                source_name TEXT,
                condition TEXT
            );
            CREATE TABLE ability_effect_link (
                id INTEGER PRIMARY KEY,
                ability_id INTEGER NOT NULL,
                effect_variant_id INTEGER NOT NULL,
                effect_source_id INTEGER
            );

            INSERT INTO ability VALUES
                (41189, 'Combat Prayer', 'Area', 10000, 37243, 2),
                (86129, 'Expansive Frost Cloak', 'Area', 20000, 86122, 1),
                (43287, 'Overflowing Altar', 'Area', 30000, 39489, 2);

            INSERT INTO effect VALUES (2, 'Berserk', 'buff');
            INSERT INTO effect_variant VALUES (3, 2, 'Minor');
            INSERT INTO effect_source VALUES (1, 'Combat Prayer', NULL);
            INSERT INTO ability_effect_link VALUES (16, 41189, 3, 1);
            """
        )


def test_combat_prayer_keeps_linked_berserk_and_adds_verified_minor_resolve(
    tmp_path: Path,
) -> None:
    path = tmp_path / 'eso.db'
    _db(path)

    effects = SkillEffectRepository(path).resolve(41189)

    assert {effect.name for effect in effects} == {'berserk', 'minor_resolve'}
    resolve = next(effect for effect in effects if effect.name == 'minor_resolve')
    assert resolve.magnitude == 2974.0
    assert resolve.duration == 10.0
    assert resolve.source == 'Combat Prayer'


def test_expansive_frost_cloak_resolves_verified_major_resolve_without_link(
    tmp_path: Path,
) -> None:
    path = tmp_path / 'eso.db'
    _db(path)

    effects = SkillEffectRepository(path).resolve(86129)

    assert [effect.name for effect in effects] == ['major_resolve']
    effect = effects[0]
    assert effect.magnitude == 5948.0
    assert effect.duration == 20.0
    assert effect.source == 'Expansive Frost Cloak'


def test_overflowing_altar_resolves_verified_minor_lifesteal_without_link(
    tmp_path: Path,
) -> None:
    path = tmp_path / 'eso.db'
    _db(path)

    effects = SkillEffectRepository(path).resolve(43287)

    assert [effect.name for effect in effects] == ['minor_lifesteal']
    effect = effects[0]
    assert effect.magnitude == 600.0
    assert effect.duration == 30.0
    assert effect.source == 'Overflowing Altar'
    assert effect.condition == 'damage_affected_enemy'
