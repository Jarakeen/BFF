from __future__ import annotations

import pytest

from models.build_model import GearSlot, PlayerBuild
from services.extreme_blueprint_service import ExtremeBlueprintService
from services.extreme_optimization_service import ExtremeOptimizationService
from ui.extreme_critical_profile_support import critical_profile_rating, install


def _profiled_build() -> PlayerBuild:
    install()
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)
    objective = ExtremeOptimizationService.objective("spell_critical")
    build = PlayerBuild(Name="Jane / John Doe", BuildName="Extreme Spell Critical Blueprint")
    profiled, label, candidates = service._apply_resting_profile(build, objective, active_bar="front")
    assert label == "Nightblade"
    assert candidates == ("Nightblade",)
    return profiled


def test_spell_critical_profile_uses_nightblade_light_armor_and_dual_daggers():
    build = _profiled_build()

    assert build.EsoClass == "Nightblade"
    assert len([skill for skill in build.FrontBarSkills if skill]) == 6
    assert len([skill for skill in build.BackBarSkills if skill]) == 6
    assert "Relentless Focus" in build.FrontBarSkills
    assert all(entry["Weight"] == "Light" for entry in build.Armor.values())
    assert build.FrontBarWeapon.WeaponType == "Dagger"
    assert build.FrontBarOffHand.WeaponType == "Dagger"
    assert build.BackBarWeapon.WeaponType == "Dagger"
    assert build.BackBarOffHand.WeaponType == "Dagger"


def test_spell_critical_profile_rating_counts_pressure_points_major_crit_and_daggers():
    build = _profiled_build()

    assert critical_profile_rating(build, active_bar="front") == pytest.approx(
        (6 * 438) + 2629 + (2 * 657)
    )


def test_spell_critical_profile_rating_only_counts_selected_active_bar():
    build = _profiled_build()
    build.BackBarSkills = []
    build.BackBarWeapon = GearSlot(WeaponType="Inferno Staff")
    build.BackBarOffHand = GearSlot()

    assert critical_profile_rating(build, active_bar="back") == 0.0
    assert critical_profile_rating(build, active_bar="front") > 0.0
