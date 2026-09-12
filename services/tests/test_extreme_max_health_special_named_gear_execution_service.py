from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_gear_search_state_rule_service import ExtremeGearSearchStateRule
from services.extreme_max_health_special_named_gear_branch_service import (
    ExtremeMaxHealthSpecialBranchKind,
    ExtremeMaxHealthSpecialNamedGearBranch,
    ExtremeMaxHealthSpecialNamedGearBranchResult,
)
from services.extreme_max_health_special_named_gear_execution_service import (
    ExtremeMaxHealthSpecialNamedGearExecutionService,
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
        self.calls = 0

    def build(self, objective_key, *, build, active_bar="front", food="", route=None):
        self.calls += 1
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


def _classified(*branches: ExtremeMaxHealthSpecialNamedGearBranch):
    return ExtremeMaxHealthSpecialNamedGearBranchResult(
        branches=tuple(branches),
        requested_pairs=tuple(
            (row.set_id, row.set_name, row.piece_count) for row in branches
        ),
    )


def test_conditional_branch_uses_canonical_runtime_projection() -> None:
    runtime = _RuntimeProjector(
        required=("food_buff_active",),
        active=("food_buff_active",),
    )
    service = ExtremeMaxHealthSpecialNamedGearExecutionService(
        runtime_condition_service=runtime,
    )
    branch = ExtremeMaxHealthSpecialNamedGearBranch(
        set_id=287,
        set_name="Green Pact",
        piece_count=5,
        kind=ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_FLAT,
        value=2500.0,
        condition="food_buff_active",
    )

    result = service.execute(_classified(branch), build=PlayerBuild(), food="Food")

    assert runtime.calls == 1
    assert result.denominator_executable is True
    assert result.executions[0].runtime_projection is not None
    assert "food_buff_active" in result.executions[0].runtime_projection.active_conditions


def test_conditional_branch_fails_closed_when_required_condition_is_not_active() -> None:
    runtime = _RuntimeProjector(
        required=("armor_ability_slotted",),
        active=(),
    )
    service = ExtremeMaxHealthSpecialNamedGearExecutionService(
        runtime_condition_service=runtime,
    )
    branch = ExtremeMaxHealthSpecialNamedGearBranch(
        set_id=178,
        set_name="Armor Master",
        piece_count=5,
        kind=ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_PERCENT,
        value=5.0,
        condition="armor_ability_slotted",
    )

    result = service.execute(_classified(branch), build=PlayerBuild())

    assert result.denominator_executable is False
    assert any(
        "required special-gear condition is not active" in item
        for item in result.unresolved
    )


def test_conditional_bundle_requires_every_runtime_marker() -> None:
    runtime = _RuntimeProjector(
        required=("food_buff_active", "armor_ability_slotted"),
        active=("food_buff_active", "armor_ability_slotted"),
    )
    service = ExtremeMaxHealthSpecialNamedGearExecutionService(
        runtime_condition_service=runtime,
    )
    branch = ExtremeMaxHealthSpecialNamedGearBranch(
        set_id=999,
        set_name="Synthetic Bundle",
        piece_count=5,
        kind=ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_BUNDLE,
        required_conditions=("food_buff_active", "armor_ability_slotted"),
    )

    result = service.execute(_classified(branch), build=PlayerBuild(), food="Food")

    assert runtime.calls == 1
    assert result.denominator_executable is True
    assert not result.unresolved


def test_conditional_bundle_fails_closed_when_any_marker_is_missing() -> None:
    runtime = _RuntimeProjector(
        required=("food_buff_active", "armor_ability_slotted"),
        active=("food_buff_active",),
    )
    service = ExtremeMaxHealthSpecialNamedGearExecutionService(
        runtime_condition_service=runtime,
    )
    branch = ExtremeMaxHealthSpecialNamedGearBranch(
        set_id=999,
        set_name="Synthetic Bundle",
        piece_count=5,
        kind=ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_BUNDLE,
        required_conditions=("food_buff_active", "armor_ability_slotted"),
    )

    result = service.execute(_classified(branch), build=PlayerBuild(), food="Food")

    assert result.denominator_executable is False
    assert any("armor_ability_slotted" in item for item in result.unresolved)


def test_twice_born_branch_dispatches_to_existing_two_mundus_executor() -> None:
    runtime = _RuntimeProjector(required=(), active=())
    service = ExtremeMaxHealthSpecialNamedGearExecutionService(
        runtime_condition_service=runtime,
    )
    branch = ExtremeMaxHealthSpecialNamedGearBranch(
        set_id=161,
        set_name="Twice-Born Star",
        piece_count=5,
        kind=ExtremeMaxHealthSpecialBranchKind.SEARCH_STATE_MUTATION,
        search_state_rule=ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS,
    )

    result = service.execute(_classified(branch), build=PlayerBuild())

    assert runtime.calls == 0
    assert result.denominator_executable is True
    execution = result.executions[0]
    assert execution.search_state_rule is ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS
    assert "ExtremeTwiceBornMundusStructuralStatEvaluator" in execution.execution_owner


def test_classifier_unresolved_state_keeps_execution_denominator_open() -> None:
    runtime = _RuntimeProjector(required=(), active=())
    service = ExtremeMaxHealthSpecialNamedGearExecutionService(
        runtime_condition_service=runtime,
    )
    classified = ExtremeMaxHealthSpecialNamedGearBranchResult(
        branches=(),
        requested_pairs=((999, "Unknown", 5),),
        unresolved=("unknown branch",),
    )

    result = service.execute(classified, build=PlayerBuild())

    assert result.denominator_executable is False
    assert result.unresolved == ("unknown branch",)
