from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_gear_search_state_rule_service import ExtremeGearSearchStateRule
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialBranchKind,
    ExtremeMaxResourceSpecialNamedGearBranch,
    ExtremeMaxResourceSpecialNamedGearBranchResult,
)
from services.extreme_max_resource_special_named_gear_execution_service import (
    ExtremeMaxResourceSpecialNamedGearExecutionService,
)
from services.extreme_resource_candidate_runtime_condition_service import (
    ExtremeResourceCandidateRuntimeConditionProjection,
)
from services.extreme_resource_runtime_condition_state_service import (
    ExtremeResourceRuntimeConditionState,
)


class _RuntimeProjector:
    def __init__(self, *, required: tuple[str, ...], active: tuple[str, ...]) -> None:
        self.required = required
        self.active = active
        self.objectives: list[str] = []

    def build(self, objective_key, *, build, active_bar="front", food="", route=None):
        self.objectives.append(str(objective_key))
        state = ExtremeResourceRuntimeConditionState(
            objective_key=str(objective_key),
            required_conditions=self.required,
            active_conditions=self.active,
        )
        return ExtremeResourceCandidateRuntimeConditionProjection(
            objective_key=str(objective_key),
            candidate_effects=(),
            state=state,
            build=build,
            denominator_proven=True,
        )


def _classified(objective: str, branch: ExtremeMaxResourceSpecialNamedGearBranch):
    return ExtremeMaxResourceSpecialNamedGearBranchResult(
        objective_key=objective,
        branches=(branch,),
        requested_pairs=((branch.set_id, branch.set_name, branch.piece_count),),
    )


def test_magicka_conditional_branch_uses_magicka_runtime_projection() -> None:
    runtime = _RuntimeProjector(required=("pet_active",), active=("pet_active",))
    service = ExtremeMaxResourceSpecialNamedGearExecutionService(
        runtime_condition_service=runtime,
    )
    branch = ExtremeMaxResourceSpecialNamedGearBranch(
        objective_key="max_magicka",
        set_id=98,
        set_name="Necropotence",
        piece_count=5,
        kind=ExtremeMaxResourceSpecialBranchKind.CONDITIONAL_BUNDLE,
        required_conditions=("pet_active",),
    )

    result = service.execute(_classified("max_magicka", branch), build=PlayerBuild())

    assert runtime.objectives == ["max_magicka"]
    assert result.denominator_executable is True
    assert not result.unresolved


def test_stamina_drink_branch_uses_stamina_runtime_projection() -> None:
    runtime = _RuntimeProjector(
        required=("drink_buff_active",),
        active=("drink_buff_active",),
    )
    service = ExtremeMaxResourceSpecialNamedGearExecutionService(
        runtime_condition_service=runtime,
    )
    branch = ExtremeMaxResourceSpecialNamedGearBranch(
        objective_key="max_stamina",
        set_id=308,
        set_name="Bone Pirate's Tatters",
        piece_count=5,
        kind=ExtremeMaxResourceSpecialBranchKind.CONDITIONAL_BUNDLE,
        required_conditions=("drink_buff_active",),
    )

    result = service.execute(
        _classified("max_stamina", branch),
        build=PlayerBuild(),
        food="Drink",
    )

    assert runtime.objectives == ["max_stamina"]
    assert result.denominator_executable is True


def test_twice_born_dispatch_is_shared_across_resource_objectives() -> None:
    runtime = _RuntimeProjector(required=(), active=())
    service = ExtremeMaxResourceSpecialNamedGearExecutionService(
        runtime_condition_service=runtime,
    )
    branch = ExtremeMaxResourceSpecialNamedGearBranch(
        objective_key="max_stamina",
        set_id=161,
        set_name="Twice-Born Star",
        piece_count=5,
        kind=ExtremeMaxResourceSpecialBranchKind.SEARCH_STATE_MUTATION,
        search_state_rule=ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS,
    )

    result = service.execute(_classified("max_stamina", branch), build=PlayerBuild())

    assert runtime.objectives == []
    assert result.denominator_executable is True
    assert "ExtremeTwiceBornMundusStructuralStatEvaluator" in result.executions[0].execution_owner
