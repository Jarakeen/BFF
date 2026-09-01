from __future__ import annotations

import sqlite3
from pathlib import Path

from minmax.character_build.effect_layer import EffectLayer
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_known_effects import (
    MAGMA_INCARNATE_SET_ID,
    MAGMA_INCARNATE_TWO_PIECE_BONUS_ID,
    SERPENTS_DISDAIN_FIVE_PIECE_BONUS_ID,
    SERPENTS_DISDAIN_SET_ID,
    SPAULDER_OF_RUIN_ONE_PIECE_BONUS_ID,
    SPAULDER_OF_RUIN_SET_ID,
)
from minmax.gear_set_repository import GearSetRepository
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType


def _make_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY,
                set_id INTEGER NOT NULL,
                piece_count INTEGER NOT NULL,
                description TEXT
            );
            """
        )
        db.executemany(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (?, ?, ?, ?)",
            [
                (MAGMA_INCARNATE_SET_ID, "Magma Incarnate", "standard", 2),
                (SPAULDER_OF_RUIN_SET_ID, "Spaulder of Ruin", "standard", 1),
                (SERPENTS_DISDAIN_SET_ID, "Serpent's Disdain", "standard", 5),
            ],
        )
        db.executemany(
            "INSERT INTO gear_set_bonus(id, set_id, piece_count, description) VALUES (?, ?, ?, ?)",
            [
                (
                    MAGMA_INCARNATE_TWO_PIECE_BONUS_ID,
                    MAGMA_INCARNATE_SET_ID,
                    2,
                    "verified Magma Incarnate two-piece row",
                ),
                (
                    SPAULDER_OF_RUIN_ONE_PIECE_BONUS_ID,
                    SPAULDER_OF_RUIN_SET_ID,
                    1,
                    "verified Spaulder of Ruin one-piece row",
                ),
                (
                    SERPENTS_DISDAIN_FIVE_PIECE_BONUS_ID,
                    SERPENTS_DISDAIN_SET_ID,
                    5,
                    "verified Serpent's Disdain five-piece row",
                ),
            ],
        )


def _resolver(path: Path) -> GearSetEffectVariantResolver:
    return GearSetEffectVariantResolver(GearSetRepository(path))


def test_magma_two_piece_resolves_both_verified_group_buffs(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _make_db(database)

    variants = _resolver(database).resolve(MAGMA_INCARNATE_SET_ID, 2)

    assert {variant.name for variant in variants} == {
        "minor_courage",
        "minor_resolve",
    }
    by_name = {variant.name: variant for variant in variants}

    courage = by_name["minor_courage"]
    assert courage.magnitude == 215.0
    assert courage.duration == 10.0
    assert courage.cooldown == 15.0
    assert courage.target_count == 4
    assert courage.range == 28.0
    assert courage.target_type == SupportTargetType.GROUP
    assert courage.category == SupportEffectCategory.BUFF
    assert courage.trigger == "single_target_heal_self_or_group_member"

    resolve = by_name["minor_resolve"]
    assert resolve.magnitude == 2974.0
    assert resolve.duration == 10.0
    assert resolve.cooldown == 15.0
    assert resolve.target_count == 4
    assert resolve.target_type == SupportTargetType.GROUP


def test_one_piece_magma_does_not_receive_two_piece_effects(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _make_db(database)

    assert _resolver(database).resolve(MAGMA_INCARNATE_SET_ID, 1) == []


def test_spaulder_resolves_verified_aura_of_pride_group_damage_buff(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _make_db(database)

    variants = _resolver(database).resolve(SPAULDER_OF_RUIN_SET_ID, 1)

    assert len(variants) == 1
    variant = variants[0]
    assert variant.name == "weapon_spell_damage"
    assert variant.magnitude == 260.0
    assert variant.target_count == 6
    assert variant.range == 12.0
    assert variant.condition == "aura_of_pride_active"
    assert variant.trigger == "crouch_or_prowl_toggle"
    assert variant.target_type == SupportTargetType.GROUP
    assert variant.category == SupportEffectCategory.BUFF


def test_serpents_disdain_resolves_verified_status_duration_modifier(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _make_db(database)

    variants = _resolver(database).resolve(SERPENTS_DISDAIN_SET_ID, 5)

    assert len(variants) == 1
    variant = variants[0]
    assert variant.name == "status_effect_duration_increase"
    assert variant.layer == EffectLayer.PASSIVE
    assert variant.magnitude == 16.0
    assert variant.target_type == SupportTargetType.SELF
    assert variant.category == SupportEffectCategory.OTHER
    assert "16 seconds" in (variant.scaling or "")
