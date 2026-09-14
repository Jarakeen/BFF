from minmax.rotation_action_occupancy import RotationActionOccupancyRequirement
from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_action_target_legality import (
    RotationActionTargetRequirement,
    RotationTargetKind,
    RotationTargetStateWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_runtime_executable_choice_service import (
    RotationRuntimeExecutableChoiceService,
)
from services.rotation_runtime_execution_strategy_service import (
    RotationRuntimeExecutionStrategyCandidate,
    RotationRuntimeExecutionStrategyResolution,
)
from services.rotation_runtime_trigger_condition_service import RotationRuntimeActivatedIntent
from services.rotation_runtime_triggered_intent_service import RotationRuntimeTriggeredIntent


def _activated(time_seconds=37.25):
    return RotationRuntimeActivatedIntent(
        intent=RotationRuntimeTriggeredIntent(
            intent_id="xalvakka:pack_encounter_adds:iron_atronach",
            trigger_key="encounter_actor_active:iron_atronach",
            directive="acquire_and_maintain_owned_add_when_active",
            source_plan_id="performance-mode-rg",
            source_seat_id="off-tank",
            encounter_id="xalvakka",
            target_key="Iron Atronach",
            required_capability_type="taunt",
        ),
        activated_at_seconds=time_seconds,
        trigger_source="authoritative runtime actor activity",
    )


def _candidate(skill="Pierce Armor", bar="front", time_seconds=37.25):
    return RotationRuntimeExecutionStrategyCandidate(
        intent_id="xalvakka:pack_encounter_adds:iron_atronach",
        activated_at_seconds=time_seconds,
        directive="acquire_and_maintain_owned_add_when_active",
        capability_type="taunt",
        skill_name=skill,
        bar=bar,
        target_key="Iron Atronach",
    )


def _strategy(*candidates):
    return RotationRuntimeExecutionStrategyResolution(
        activated_intent=_activated(),
        candidates=tuple(candidates),
    )


def _plan(*actions):
    return RotationPlan(
        character_name="Rylonia",
        build_name="Tank Build",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def _slot(skill="Pierce Armor", *bars):
    return RotationActionSlotRequirement(
        action_name=skill,
        allowed_bars=tuple(bars or ("front",)),
    )


def _target(skill="Pierce Armor", bar="front"):
    return RotationActionTargetRequirement(
        action_name=skill,
        action_kind=RotationActionKind.SKILL,
        bar=bar,
        allowed_targets=(RotationTargetKind.ENEMY,),
    )


def _window(kind=RotationTargetKind.ENEMY):
    return RotationTargetStateWindow(
        name="Iron Atronach active",
        start_seconds=37.0,
        end_seconds=50.0,
        target_kind=kind,
    )


def _occupancy(skill="Pierce Armor", bar="front", seconds=0.0):
    return RotationActionOccupancyRequirement(
        action_name=skill,
        action_kind=RotationActionKind.SKILL,
        bar=bar,
        occupancy_seconds=seconds,
    )


def test_single_same_bar_candidate_with_complete_legality_is_selected() -> None:
    candidate = _candidate()
    result = RotationRuntimeExecutableChoiceService().resolve(
        plan=_plan(),
        strategy=_strategy(candidate),
        slot_requirements=(_slot("Pierce Armor", "front"),),
        target_requirements=(_target(),),
        target_windows=(_window(),),
        occupancy_requirements=(_occupancy(),),
    )

    assert result.resolved is True
    assert result.selected is not None
    assert result.selected.candidate is candidate
    assert result.selected.active_bar == "front"
    assert result.executable_candidates == (candidate,)
    assert result.requires_bar_swap == ()
    assert not hasattr(result.selected, "time_seconds")


def test_inactive_bar_candidate_requires_explicit_bar_swap_policy() -> None:
    candidate = _candidate(skill="Inner Rage", bar="back")
    result = RotationRuntimeExecutableChoiceService().resolve(
        plan=_plan(),
        strategy=_strategy(candidate),
        slot_requirements=(_slot("Inner Rage", "back"),),
        target_requirements=(_target("Inner Rage", "back"),),
        target_windows=(_window(),),
        occupancy_requirements=(_occupancy("Inner Rage", "back"),),
    )

    assert result.selected is None
    assert result.requires_bar_swap == (candidate,)
    assert "bar-swap execution policy" in result.unresolved[0]


def test_missing_target_state_evidence_fails_closed() -> None:
    candidate = _candidate()
    result = RotationRuntimeExecutableChoiceService().resolve(
        plan=_plan(),
        strategy=_strategy(candidate),
        slot_requirements=(_slot("Pierce Armor", "front"),),
        target_requirements=(_target(),),
        target_windows=(),
        occupancy_requirements=(_occupancy(),),
    )

    assert result.selected is None
    assert "target-state evidence is missing" in result.unresolved[0]


def test_existing_occupancy_collision_blocks_activation() -> None:
    existing = RotationAction(
        time_seconds=37.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Defensive Posture",
        bar="front",
    )
    candidate = _candidate()
    result = RotationRuntimeExecutableChoiceService().resolve(
        plan=_plan(existing),
        strategy=_strategy(candidate),
        slot_requirements=(_slot("Pierce Armor", "front"),),
        target_requirements=(_target(),),
        target_windows=(_window(),),
        occupancy_requirements=(
            _occupancy("Defensive Posture", "front", 1.0),
            _occupancy("Pierce Armor", "front", 0.0),
        ),
    )

    assert result.selected is None
    assert "conflicts with action occupancy" in result.unresolved[0]


def test_multiple_same_bar_legal_candidates_require_explicit_execution_policy() -> None:
    pierce = _candidate("Pierce Armor", "front")
    inner = _candidate("Inner Rage", "front")
    result = RotationRuntimeExecutableChoiceService().resolve(
        plan=_plan(),
        strategy=_strategy(pierce, inner),
        slot_requirements=(
            _slot("Pierce Armor", "front"),
            _slot("Inner Rage", "front"),
        ),
        target_requirements=(
            _target("Pierce Armor", "front"),
            _target("Inner Rage", "front"),
        ),
        target_windows=(_window(),),
        occupancy_requirements=(
            _occupancy("Pierce Armor", "front", 0.0),
            _occupancy("Inner Rage", "front", 0.0),
        ),
    )

    assert result.selected is None
    assert result.executable_candidates == (pierce, inner)
    assert "multiple runtime strategy candidates" in result.unresolved[0]


def test_active_bar_progression_is_reused_from_existing_plan() -> None:
    swap = RotationAction(
        time_seconds=20.0,
        sequence=0,
        kind=RotationActionKind.BAR_SWAP,
        bar="back",
    )
    candidate = _candidate("Inner Rage", "back")
    result = RotationRuntimeExecutableChoiceService().resolve(
        plan=_plan(swap),
        strategy=_strategy(candidate),
        slot_requirements=(_slot("Inner Rage", "back"),),
        target_requirements=(_target("Inner Rage", "back"),),
        target_windows=(_window(),),
        occupancy_requirements=(_occupancy("Inner Rage", "back", 0.0),),
    )

    assert result.resolved is True
    assert result.selected is not None
    assert result.selected.active_bar == "back"
