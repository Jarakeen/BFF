import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_runtime_action_materialization_service import (
    RotationRuntimeActionMaterializationService,
)
from services.rotation_runtime_executable_choice_service import (
    RotationRuntimeExecutableChoice,
)
from services.rotation_runtime_execution_strategy_service import (
    RotationRuntimeExecutionStrategyCandidate,
)


def _choice(
    *,
    time_seconds: float = 37.25,
    skill_name: str = "Pierce Armor",
    bar: str = "front",
    target_key: str | None = "Iron Atronach",
) -> RotationRuntimeExecutableChoice:
    return RotationRuntimeExecutableChoice(
        candidate=RotationRuntimeExecutionStrategyCandidate(
            intent_id="xalvakka:pack_encounter_adds:iron_atronach",
            activated_at_seconds=time_seconds,
            directive="acquire_and_maintain_owned_add_when_active",
            capability_type="taunt",
            skill_name=skill_name,
            bar=bar,
            target_key=target_key,
        ),
        active_bar=bar,
    )


def _plan(*actions: RotationAction, duration: float = 60.0) -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Tank Build",
        duration_seconds=duration,
        actions=tuple(actions),
        assumptions=("caller supplied runtime trigger evidence",),
        unresolved=("unrelated existing diagnostic",),
    )


def test_materializes_proven_choice_as_exact_skill_action_without_mutating_seed_plan() -> None:
    seed = _plan()

    result = RotationRuntimeActionMaterializationService().materialize(
        plan=seed,
        choice=_choice(),
    )

    assert result.inserted is True
    assert seed.actions == ()
    assert result.plan is not seed
    assert result.action.time_seconds == 37.25
    assert result.action.sequence == 0
    assert result.action.kind is RotationActionKind.SKILL
    assert result.action.name == "Pierce Armor"
    assert result.action.bar == "front"
    assert result.action.target_key == "Iron Atronach"
    assert result.plan.actions == (result.action,)
    assert result.plan.assumptions == seed.assumptions
    assert result.plan.unresolved == seed.unresolved


def test_materialization_uses_next_sequence_at_existing_activation_timestamp() -> None:
    existing_la = RotationAction(
        time_seconds=37.25,
        sequence=0,
        kind=RotationActionKind.LIGHT_ATTACK,
        bar="front",
        target_key="Iron Atronach",
    )
    existing_wait = RotationAction(
        time_seconds=37.25,
        sequence=4,
        kind=RotationActionKind.WAIT,
    )
    seed = _plan(existing_la, existing_wait)

    result = RotationRuntimeActionMaterializationService().materialize(
        plan=seed,
        choice=_choice(),
    )

    assert result.action.sequence == 5
    assert [action.sequence for action in result.plan.actions if action.time_seconds == 37.25] == [0, 4, 5]


def test_repeated_materialization_of_same_exact_action_is_idempotent() -> None:
    service = RotationRuntimeActionMaterializationService()
    first = service.materialize(plan=_plan(), choice=_choice())

    second = service.materialize(plan=first.plan, choice=_choice())

    assert second.inserted is False
    assert second.plan is first.plan
    assert second.action == first.action
    assert len(second.plan.actions) == 1


def test_action_may_materialize_exactly_at_plan_end() -> None:
    result = RotationRuntimeActionMaterializationService().materialize(
        plan=_plan(duration=37.25),
        choice=_choice(time_seconds=37.25),
    )

    assert result.inserted is True
    assert result.action.time_seconds == 37.25


def test_choice_after_plan_duration_is_rejected() -> None:
    with pytest.raises(ValueError, match="after the deterministic plan duration"):
        RotationRuntimeActionMaterializationService().materialize(
            plan=_plan(duration=30.0),
            choice=_choice(time_seconds=37.25),
        )


def test_duplicate_matching_actions_already_in_plan_fail_closed() -> None:
    duplicate_one = RotationAction(
        time_seconds=37.25,
        sequence=1,
        kind=RotationActionKind.SKILL,
        name="Pierce Armor",
        bar="front",
        target_key="Iron Atronach",
    )
    duplicate_two = RotationAction(
        time_seconds=37.25,
        sequence=2,
        kind=RotationActionKind.SKILL,
        name="Pierce Armor",
        bar="front",
        target_key="Iron Atronach",
    )

    with pytest.raises(ValueError, match="duplicate matching runtime actions"):
        RotationRuntimeActionMaterializationService().materialize(
            plan=_plan(duplicate_one, duplicate_two),
            choice=_choice(),
        )
