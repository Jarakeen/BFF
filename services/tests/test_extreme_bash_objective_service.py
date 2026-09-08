from __future__ import annotations

import pytest

from minmax.character_build.weapon_type import WeaponType
from services.extreme_bash_objective_service import (
    ExtremeBashBarWeapons,
    ExtremeBashCostInputs,
    ExtremeBashDamageInputs,
    ExtremeBashLegalityContext,
    ExtremeBashObjectiveService,
)


def _legal_dual_bar_context() -> ExtremeBashLegalityContext:
    return ExtremeBashLegalityContext(
        front=ExtremeBashBarWeapons(WeaponType.SWORD, WeaponType.SHIELD),
        back=ExtremeBashBarWeapons(WeaponType.MACE, WeaponType.SHIELD),
    )


def test_most_bashy_dual_bar_legality_requires_one_hand_and_shield_on_both_bars():
    legal = _legal_dual_bar_context()
    illegal = ExtremeBashLegalityContext(
        front=ExtremeBashBarWeapons(WeaponType.SWORD, WeaponType.SHIELD),
        back=ExtremeBashBarWeapons(WeaponType.BOW),
    )

    assert legal.dual_bar_one_hand_and_shield is True
    assert legal.blockers() == ()
    assert illegal.dual_bar_one_hand_and_shield is False
    assert illegal.blockers() == (
        "back bar is not a legal One Hand and Shield configuration",
    )


def test_complete_bash_damage_inputs_reuse_canonical_formula():
    result = ExtremeBashObjectiveService.evaluate_damage(
        ExtremeBashDamageInputs(
            spell_resist=1000.0,
            physical_resist=2000.0,
            cp_bash_damage=0.05,
            skill2_bash_damage=0.10,
            physical_damage_done=0.05,
            damage_done=0.05,
            direct_damage_done=0.05,
            single_target_damage_done=0.05,
            skill_bash_damage=0.10,
            set_extra_bash_damage=50.0,
            skill_extra_bash_damage=25.0,
            item_extra_bash_damage=25.0,
        ),
        legality=_legal_dual_bar_context(),
    )

    base = 2000.0 * 0.011250 + 1.0 + 0.05 + 0.10
    expected = base * (1.0 + 0.05 + 0.05 + 0.05 + 0.05 + 0.10) + 100.0

    assert result.objective_key == "bash_damage"
    assert result.reviewed_value == pytest.approx(expected)
    assert result.unresolved_channels == ()
    assert result.legality_blockers == ()
    assert result.mechanic_complete is True


def test_complete_bash_cost_inputs_reuse_765_base_cost_formula():
    result = ExtremeBashObjectiveService.evaluate_cost(
        ExtremeBashCostInputs(
            item_bash_cost=100.0,
            cp_bash_cost=-0.10,
            skill_bash_cost=-0.20,
            set_bash_cost=-0.30,
        ),
        legality=_legal_dual_bar_context(),
    )

    expected = 865.0 * 0.90 * 0.80 * 0.70
    assert result.objective_key == "bash_cost"
    assert result.reviewed_value == pytest.approx(expected)
    assert result.mechanic_complete is True


def test_missing_bash_channels_remain_blockers_instead_of_becoming_proven_zero():
    result = ExtremeBashObjectiveService.evaluate_damage(
        ExtremeBashDamageInputs(
            spell_resist=1000.0,
            physical_resist=2000.0,
        ),
        legality=_legal_dual_bar_context(),
    )

    assert result.reviewed_value == pytest.approx(2000.0 * 0.011250 + 1.0)
    assert "cp_bash_damage" in result.unresolved_channels
    assert "set_extra_bash_damage" in result.unresolved_channels
    assert result.mechanic_complete is False


def test_illegal_back_bar_blocks_complete_most_bashy_claim_even_with_full_math():
    illegal = ExtremeBashLegalityContext(
        front=ExtremeBashBarWeapons(WeaponType.DAGGER, WeaponType.SHIELD),
        back=ExtremeBashBarWeapons(WeaponType.RESTORATION_STAFF),
    )
    result = ExtremeBashObjectiveService.evaluate_cost(
        ExtremeBashCostInputs(
            item_bash_cost=0.0,
            cp_bash_cost=0.0,
            skill_bash_cost=0.0,
            set_bash_cost=0.0,
        ),
        legality=illegal,
    )

    assert result.reviewed_value == pytest.approx(765.0)
    assert result.unresolved_channels == ()
    assert result.legality_blockers == (
        "back bar is not a legal One Hand and Shield configuration",
    )
    assert result.mechanic_complete is False
