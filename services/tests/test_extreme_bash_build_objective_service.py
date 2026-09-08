from __future__ import annotations

import pytest

from services.extreme_bash_build_objective_service import ExtremeBashBuildObjectiveService
from services.extreme_bash_champion_point_service import ExtremeBashChampionPointResult
from services.extreme_bash_deadly_bash_service import ExtremeDeadlyBashResult
from services.extreme_bash_jewelry_service import ExtremeBashJewelryResult
from services.extreme_bash_objective_service import ExtremeBashCostInputs, ExtremeBashDamageInputs


def _base_inputs() -> ExtremeBashDamageInputs:
    return ExtremeBashDamageInputs(
        spell_resist=1000.0,
        physical_resist=2000.0,
        cp_bash_damage=None,
        skill2_bash_damage=0.0,
        physical_damage_done=0.0,
        damage_done=0.0,
        direct_damage_done=0.0,
        single_target_damage_done=0.0,
        skill_bash_damage=0.0,
        set_extra_bash_damage=0.0,
        skill_extra_bash_damage=0.0,
        item_extra_bash_damage=None,
    )


def test_build_objective_composes_reviewed_cp_and_jewelry_channels():
    cp = ExtremeBashChampionPointResult(name="Bashing Brutality", objective_key="bash_damage", stages=2, reviewed_formula_value=120.0, canonical_flat_value=120.0)
    jewelry = ExtremeBashJewelryResult(reviewed_item_extra_bash_damage=540.0, slots=())
    result = ExtremeBashBuildObjectiveService.evaluate_damage(_base_inputs(), champion_point=cp, jewelry=jewelry)
    assert result.reviewed_value == pytest.approx((2000.0 * 0.011250 + 1.0 + 120.0) + 540.0)
    assert result.objective.unresolved_channels == ()
    assert result.source_blockers == ()
    assert result.mechanic_complete is True


def test_build_objective_composes_deadly_bash_skill2_damage_channel():
    inputs = ExtremeBashDamageInputs(**{**_base_inputs().__dict__, "skill2_bash_damage": None})
    deadly = ExtremeDeadlyBashResult(passive_name="Deadly Bash", rank=2, skill2_bash_damage=500.0, skill_bash_cost=-0.5)
    result = ExtremeBashBuildObjectiveService.evaluate_damage(inputs, deadly_bash=deadly)
    assert result.reviewed_value == pytest.approx(2000.0 * 0.011250 + 1.0 + 500.0)
    assert result.objective.unresolved_channels == ()
    assert result.source_blockers == ()
    assert result.mechanic_complete is True


def test_build_objective_composes_deadly_bash_cost_channel():
    inputs = ExtremeBashCostInputs(item_bash_cost=0.0, cp_bash_cost=0.0, skill_bash_cost=None, set_bash_cost=0.0)
    deadly = ExtremeDeadlyBashResult(passive_name="Deadly Bash", rank=2, skill2_bash_damage=500.0, skill_bash_cost=-0.5)
    result = ExtremeBashBuildObjectiveService.evaluate_cost(inputs, deadly_bash=deadly)
    assert result.reviewed_value == pytest.approx(765.0 * 0.5)
    assert result.objective.unresolved_channels == ()
    assert result.source_blockers == ()
    assert result.mechanic_complete is True


def test_savage_defense_preserves_flat_cost_blocker_instead_of_fake_multiplier():
    inputs = ExtremeBashCostInputs(item_bash_cost=0.0, cp_bash_cost=None, skill_bash_cost=0.0, set_bash_cost=0.0)
    savage = ExtremeBashChampionPointResult(
        name="Savage Defense",
        objective_key="bash_cost",
        stages=2,
        reviewed_formula_value=None,
        canonical_flat_value=-90.0,
        unresolved=("Savage Defense flat cost stacking order requires review",),
    )
    result = ExtremeBashBuildObjectiveService.evaluate_cost(inputs, champion_point=savage)
    assert result.reviewed_value == pytest.approx(765.0)
    assert "cp_bash_cost" in result.objective.unresolved_channels
    assert result.source_blockers == ("Champion Point Savage Defense: Savage Defense flat cost stacking order requires review",)
    assert result.mechanic_complete is False


def test_unresolved_deadly_bash_keeps_skill2_channel_and_source_blocker():
    inputs = ExtremeBashDamageInputs(**{**_base_inputs().__dict__, "skill2_bash_damage": None})
    deadly = ExtremeDeadlyBashResult(passive_name="Deadly Bash", rank=None, skill2_bash_damage=None, skill_bash_cost=None, unresolved=("Passive rank is not recorded for character: Deadly Bash",))
    result = ExtremeBashBuildObjectiveService.evaluate_damage(inputs, deadly_bash=deadly)
    assert "skill2_bash_damage" in result.objective.unresolved_channels
    assert result.source_blockers == ("Deadly Bash: Passive rank is not recorded for character: Deadly Bash",)
    assert result.mechanic_complete is False


def test_build_objective_preserves_source_blockers_with_partial_jewelry_value():
    cp = ExtremeBashChampionPointResult(name="Bashing Brutality", objective_key="bash_damage", stages=2, reviewed_formula_value=120.0, canonical_flat_value=120.0)
    jewelry = ExtremeBashJewelryResult(reviewed_item_extra_bash_damage=180.0, slots=(), unresolved=("Ring 1 Bashing: needs verified level/tier scaling",))
    result = ExtremeBashBuildObjectiveService.evaluate_damage(_base_inputs(), champion_point=cp, jewelry=jewelry)
    assert result.reviewed_value > 0.0
    assert result.objective.unresolved_channels == ()
    assert result.source_blockers == ("Jewelry: Ring 1 Bashing: needs verified level/tier scaling",)
    assert result.mechanic_complete is False


def test_unresolved_cp_formula_keeps_cp_channel_and_detailed_source_blocker():
    cp = ExtremeBashChampionPointResult(name="Bashing Brutality", objective_key="bash_damage", stages=2, reviewed_formula_value=None, unresolved=("unrecognized Bashing Brutality tooltip",))
    jewelry = ExtremeBashJewelryResult(reviewed_item_extra_bash_damage=180.0, slots=())
    result = ExtremeBashBuildObjectiveService.evaluate_damage(_base_inputs(), champion_point=cp, jewelry=jewelry)
    assert "cp_bash_damage" in result.objective.unresolved_channels
    assert result.source_blockers == ("Champion Point Bashing Brutality: unrecognized Bashing Brutality tooltip",)
    assert result.mechanic_complete is False


def test_source_composition_rejects_double_counting_direct_cp_channel():
    inputs = ExtremeBashDamageInputs(**{**_base_inputs().__dict__, "cp_bash_damage": 120.0})
    cp = ExtremeBashChampionPointResult(name="Bashing Brutality", objective_key="bash_damage", stages=2, reviewed_formula_value=120.0)
    with pytest.raises(ValueError, match="supplied directly and through Champion Point"):
        ExtremeBashBuildObjectiveService.evaluate_damage(inputs, champion_point=cp)


def test_source_composition_rejects_double_counting_direct_deadly_bash_channel():
    deadly = ExtremeDeadlyBashResult(passive_name="Deadly Bash", rank=2, skill2_bash_damage=500.0, skill_bash_cost=-0.5)
    with pytest.raises(ValueError, match="supplied directly and through Deadly Bash"):
        ExtremeBashBuildObjectiveService.evaluate_damage(_base_inputs(), deadly_bash=deadly)


def test_cost_source_composition_rejects_double_counting_deadly_bash_channel():
    deadly = ExtremeDeadlyBashResult(passive_name="Deadly Bash", rank=2, skill2_bash_damage=500.0, skill_bash_cost=-0.5)
    inputs = ExtremeBashCostInputs(item_bash_cost=0.0, cp_bash_cost=0.0, skill_bash_cost=-0.5, set_bash_cost=0.0)
    with pytest.raises(ValueError, match="skill_bash_cost was supplied directly and through Deadly Bash"):
        ExtremeBashBuildObjectiveService.evaluate_cost(inputs, deadly_bash=deadly)
