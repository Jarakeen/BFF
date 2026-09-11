from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from models.build_model import PlayerBuild
from services.heavy_attack_progression_modifier_service import (
    HeavyAttackProgressionModifierService,
)


def _build(*, heavy_pieces: int = 0) -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    for index, slot in enumerate(("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")):
        build.Armor[slot]["Weight"] = "Heavy" if index < heavy_pieces else "Light"
    return build


def _progression(**ranks: int) -> CharacterProgression:
    return CharacterProgression(passive_ranks=dict(ranks))


def test_resto_cycle_of_life_rank_two_resolves_thirty_percent() -> None:
    result = HeavyAttackProgressionModifierService().resolve(
        build=_build(),
        progression=_progression(**{"Cycle of Life": 2}),
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
    )

    assert result.is_resolved is True
    assert result.cycle_of_life_rank == 2
    assert result.modifiers.restoration_staff_cycle_of_life_percent == pytest.approx(0.30)
    assert result.modifiers.heavy_armor_revitalize_percent == 0.0


def test_resto_cycle_of_life_rank_one_resolves_fifteen_percent() -> None:
    result = HeavyAttackProgressionModifierService().resolve(
        build=_build(),
        progression=_progression(**{"Cycle of Life": 1}),
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
    )

    assert result.is_resolved is True
    assert result.modifiers.restoration_staff_cycle_of_life_percent == pytest.approx(0.15)


def test_revitalize_rank_two_scales_with_equipped_heavy_pieces() -> None:
    result = HeavyAttackProgressionModifierService().resolve(
        build=_build(heavy_pieces=3),
        progression=_progression(Revitalize=2),
        weapon=HeavyAttackWeaponType.FROST_STAFF,
    )

    assert result.is_resolved is True
    assert result.heavy_armor_pieces == 3
    assert result.revitalize_rank == 2
    assert result.modifiers.heavy_armor_revitalize_percent == pytest.approx(0.12)
    assert result.modifiers.restoration_staff_cycle_of_life_percent == 0.0


def test_revitalize_rank_one_scales_two_percent_per_heavy_piece() -> None:
    result = HeavyAttackProgressionModifierService().resolve(
        build=_build(heavy_pieces=2),
        progression=_progression(Revitalize=1),
        weapon=HeavyAttackWeaponType.SHOCK_STAFF,
    )

    assert result.is_resolved is True
    assert result.modifiers.heavy_armor_revitalize_percent == pytest.approx(0.04)


def test_missing_cycle_of_life_rank_fails_closed_for_resto() -> None:
    result = HeavyAttackProgressionModifierService().resolve(
        build=_build(),
        progression=CharacterProgression(passive_ranks={}),
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
    )

    assert result.is_resolved is False
    assert result.modifiers.restoration_staff_cycle_of_life_percent == 0.0
    assert "Cycle of Life rank is unknown" in result.unresolved[0]


def test_missing_revitalize_rank_fails_closed_when_heavy_armor_is_equipped() -> None:
    result = HeavyAttackProgressionModifierService().resolve(
        build=_build(heavy_pieces=1),
        progression=CharacterProgression(passive_ranks={}),
        weapon=HeavyAttackWeaponType.FROST_STAFF,
    )

    assert result.is_resolved is False
    assert result.modifiers.heavy_armor_revitalize_percent == 0.0
    assert "Revitalize rank is unknown" in result.unresolved[0]


def test_explicit_zero_ranks_are_known_unpurchased_not_unknown() -> None:
    result = HeavyAttackProgressionModifierService().resolve(
        build=_build(heavy_pieces=2),
        progression=_progression(**{"Cycle of Life": 0, "Revitalize": 0}),
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
    )

    assert result.is_resolved is True
    assert result.modifiers.restoration_staff_cycle_of_life_percent == 0.0
    assert result.modifiers.heavy_armor_revitalize_percent == 0.0


def test_irrelevant_passives_are_not_required() -> None:
    result = HeavyAttackProgressionModifierService().resolve(
        build=_build(),
        progression=CharacterProgression(passive_ranks={}),
        weapon=HeavyAttackWeaponType.FROST_STAFF,
    )

    assert result.is_resolved is True
    assert result.unresolved == ()


def test_unsupported_passive_rank_fails_closed() -> None:
    result = HeavyAttackProgressionModifierService().resolve(
        build=_build(heavy_pieces=1),
        progression=_progression(**{"Cycle of Life": 3, "Revitalize": 3}),
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
    )

    assert result.is_resolved is False
    assert any("Cycle of Life rank is unsupported: 3" in item for item in result.unresolved)
    assert any("Revitalize rank is unsupported: 3" in item for item in result.unresolved)
