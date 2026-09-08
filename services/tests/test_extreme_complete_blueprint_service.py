from __future__ import annotations

import pytest

from services.extreme_blueprint_service import ExtremeBlueprintService
from services.extreme_complete_blueprint_service import ExtremeCompleteBlueprintService
from services.extreme_optimization_service import ExtremeOptimizationService


def _service() -> ExtremeCompleteBlueprintService:
    service = ExtremeCompleteBlueprintService.__new__(ExtremeCompleteBlueprintService)
    service.extreme = type(
        "ExtremeStub",
        (),
        {"objective": staticmethod(ExtremeOptimizationService.objective)},
    )()
    return service


def test_weapon_damage_blank_build_starts_with_weapon_damage_choices():
    service = _service()
    objective = ExtremeOptimizationService.objective("weapon_damage")

    build = service._blank_build(objective)

    assert all(entry["Enchant"] == "Max Stamina" for entry in build.Armor.values())
    assert build.Necklace.Enchant == "Weapon Damage"
    assert build.Ring1.Enchant == "Weapon Damage"
    assert build.Ring2.Enchant == "Weapon Damage"


def test_weapon_damage_reuses_reviewed_sorcerer_dual_sword_medium_profile():
    service = _service()
    objective = ExtremeOptimizationService.objective("weapon_damage")
    build = service._blank_build(objective)

    profiled, label, contenders = service._apply_resting_profile(
        build,
        objective,
        active_bar="front",
    )

    assert label == "Sorcerer"
    assert contenders == ("Sorcerer",)
    assert profiled.EsoClass == "Sorcerer"
    assert len([skill for skill in profiled.FrontBarSkills if skill]) == 6
    assert len([skill for skill in profiled.BackBarSkills if skill]) == 6
    assert profiled.FrontBarWeapon.WeaponType == "Sword"
    assert profiled.FrontBarOffHand.WeaponType == "Sword"
    assert profiled.BackBarWeapon.WeaponType == "Sword"
    assert profiled.BackBarOffHand.WeaponType == "Sword"
    assert all(entry["Weight"] == "Medium" for entry in profiled.Armor.values())
    assert profiled.Necklace.Enchant == "Weapon Damage"


def test_weapon_damage_evaluation_adds_same_reviewed_standing_bonus(monkeypatch):
    service = _service()
    objective = ExtremeOptimizationService.objective("weapon_damage")
    build = service._blank_build(objective)
    profiled, _, _ = service._apply_resting_profile(
        build,
        objective,
        active_bar="front",
    )

    monkeypatch.setattr(
        ExtremeBlueprintService,
        "_evaluate_snapshot",
        lambda self, build, **kwargs: (1000.0, ()),
    )

    value, unresolved = service._evaluate_snapshot(
        profiled,
        progression=None,
        character_id="test",
        build_id="test",
        objective=objective,
        active_bar="front",
    )

    assert unresolved == ()
    assert value == pytest.approx(1000.0 + ((6 * 108) + (2 * 129)) * 1.14)


def test_weapon_power_potion_percent_applies_to_reviewed_standing_bonus(monkeypatch):
    service = _service()
    objective = ExtremeOptimizationService.objective("weapon_damage")
    build = service._blank_build(objective)
    profiled, _, _ = service._apply_resting_profile(
        build,
        objective,
        active_bar="front",
    )

    monkeypatch.setattr(
        ExtremeBlueprintService,
        "_evaluate_snapshot",
        lambda self, build, **kwargs: (1000.0, ()),
    )

    value, _ = service._evaluate_snapshot(
        profiled,
        progression=None,
        character_id="test",
        build_id="test",
        objective=objective,
        active_bar="front",
        potion_buff="Major Brutality",
    )

    assert value == pytest.approx(1000.0 + ((6 * 108) + (2 * 129)) * 1.34)
