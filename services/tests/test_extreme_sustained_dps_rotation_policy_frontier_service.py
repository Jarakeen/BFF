from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.ultimate_resource_timeline import UltimateSpendRule
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_rotation_plan_frontier_service import (
    ExtremeSustainedDPSRotationPlanCandidate,
)
from services.extreme_sustained_dps_rotation_policy_frontier_service import (
    ExtremeSustainedDPSRotationPolicyFrontierService,
)


def _plan():
    return RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=12.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(0.0, 1, RotationActionKind.SKILL, name="A", bar="front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, name="B", bar="front"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, name="C", bar="front"),
        ),
    )


def _seed():
    return ExtremeSustainedDPSRotationPlanCandidate(
        structural_index=0,
        front_order=("A", "B", "C"),
        back_order=(),
        starting_bar="front",
        weave_light_attacks=True,
        plan=_plan(),
        evidence=(),
        unresolved=(),
    )


def _build(*, potion=True, ultimate=True):
    build = PlayerBuild(
        Name="Generated",
        BuildName="Candidate",
        Role="DD",
        Potion="Potion X" if potion else "",
    )
    build.FrontBarSkills = ["A", "B", "C", "", "", "Ultimate X" if ultimate else ""]
    build.BackBarSkills = ["", "", "", "", "", ""]
    return build


class _UltimateService:
    def resolve_generation_inputs(self, **kwargs):
        bar = kwargs["ultimate_bar"]
        return SimpleNamespace(
            bar=bar,
            slotted_ultimate="Ultimate X",
            spend_rule=UltimateSpendRule("Ultimate X", 100.0),
            generation_events=(),
            unresolved=(),
        )

    def apply_generation(self, **kwargs):
        plan = kwargs["plan"]
        projected = RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=plan.actions,
            unresolved=(
                "shared Ultimate projection selected front-bar 'Ultimate X'; competing back-bar ultimate 'Other' choice policy is unresolved",
            ),
        )
        return SimpleNamespace(
            plan=projected,
            unresolved=projected.unresolved,
            generation_events=(),
            spend_rules=(),
        )


class _Legality:
    def assess(self, **kwargs):
        plan = kwargs["plan"]
        potion_times = tuple(
            action.time_seconds
            for action in plan.actions
            if action.kind is RotationActionKind.POTION
        )
        legal = all(
            b - a + 1e-9 >= kwargs["potion_cooldown_seconds"]
            for a, b in zip(potion_times, potion_times[1:])
        )
        return SimpleNamespace(
            is_legal=legal,
            unresolved=(),
        )


def _service():
    return ExtremeSustainedDPSRotationPolicyFrontierService(
        ultimate_service=_UltimateService(),
        legality_service=_Legality(),
    )


def test_policy_frontier_preserves_ultimate_choice_and_anchored_potion_ordering() -> None:
    result = _service().frontier(
        build=_build(),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
    )

    assert result.ultimate_options == ("none", "front")
    # no-use + before/after at 0,1,2 seconds
    assert len(result.potion_policies) == 7
    assert result.candidate_count == 14
    assert result.anchored_policy_denominator_proven is True
    assert result.continuous_potion_timing_closed is False
    assert result.delayed_ultimate_timing_closed is True


def test_before_potion_order_shifts_existing_same_timestamp_sequence() -> None:
    service = _service()
    policy = service.frontier(
        build=_build(),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
    ).potion_policies[1]
    candidate = service.candidate_at(
        build=_build(),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
        starting_ultimate=0.0,
        index=1,
    )

    zero = tuple(
        action
        for action in candidate.plan.actions
        if abs(action.time_seconds) <= 1e-9
    )
    assert policy.same_timestamp_order == "before"
    assert zero[0].kind is RotationActionKind.POTION
    assert tuple(action.sequence for action in zero) == (0, 1, 2)


def test_after_potion_order_preserves_existing_action_sequence() -> None:
    candidate = _service().candidate_at(
        build=_build(),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
        starting_ultimate=0.0,
        index=2,
    )

    zero = tuple(
        action
        for action in candidate.plan.actions
        if abs(action.time_seconds) <= 1e-9
    )
    assert tuple(action.kind for action in zero) == (
        RotationActionKind.LIGHT_ATTACK,
        RotationActionKind.SKILL,
        RotationActionKind.POTION,
    )
    assert tuple(action.sequence for action in zero) == (0, 1, 2)


def test_potion_policy_repeats_at_proven_effective_cooldown() -> None:
    candidate = _service().candidate_at(
        build=_build(),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
        starting_ultimate=0.0,
        index=1,
    )

    potion_times = tuple(
        action.time_seconds
        for action in candidate.plan.actions
        if action.kind is RotationActionKind.POTION
    )
    assert potion_times == (0.0, 10.0)
    assert candidate.resource_legality.is_legal is True


def test_explicit_ultimate_choice_clears_only_competing_choice_diagnostic() -> None:
    frontier = _service().frontier(
        build=_build(potion=False),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
    )
    assert frontier.candidate_count == 2

    candidate = _service().candidate_at(
        build=_build(potion=False),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
        starting_ultimate=0.0,
        index=1,
    )

    assert candidate.ultimate_option == "front"
    assert all(
        "choice policy is unresolved" not in row.casefold()
        for row in candidate.unresolved
    )


def test_no_potion_build_has_only_no_use_policy() -> None:
    result = _service().frontier(
        build=_build(potion=False, ultimate=False),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
    )

    assert result.ultimate_options == ("none",)
    assert len(result.potion_policies) == 1
    assert result.candidate_count == 1


def test_invalid_policy_index_fails_closed() -> None:
    service = _service()
    frontier = service.frontier(
        build=_build(),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
    )
    with pytest.raises(IndexError):
        service.candidate_at(
            build=_build(),
            seed=_seed(),
            potion_cooldown_seconds=10.0,
            starting_ultimate=0.0,
            index=frontier.candidate_count,
        )



def test_delayed_ultimate_timing_expands_exact_seed_plan_family() -> None:
    result = _service().frontier(
        build=_build(potion=False),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
        starting_ultimate=100.0,
    )

    assert result.delayed_ultimate_timing_closed is True
    assert tuple(
        row.policy_id
        for row in result.ultimate_timing_policies
    ) == (
        "ultimate:none",
        "front:ultimate:none",
        "front:ultimate:0/1",
        "front:ultimate:1/0",
        "front:ultimate:2/0",
    )
    assert result.candidate_count == 5


def test_delayed_ultimate_candidate_materializes_selected_cast_slot() -> None:
    service = _service()
    frontier = service.frontier(
        build=_build(potion=False),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
        starting_ultimate=100.0,
    )
    index = next(
        i
        for i, row in enumerate(frontier.ultimate_timing_policies)
        if row.policy_id == "front:ultimate:2/0"
    )

    candidate = service.candidate_at(
        build=_build(potion=False),
        seed=_seed(),
        potion_cooldown_seconds=10.0,
        starting_ultimate=100.0,
        index=index,
    )

    casts = tuple(
        action
        for action in candidate.plan.actions
        if action.kind is RotationActionKind.ULTIMATE
    )
    assert len(casts) == 1
    assert casts[0].time_seconds == 2.0
    assert candidate.resource_legality.is_legal is True


def test_rotation_policy_frontier_rejects_boolean_candidate_index() -> None:
    with pytest.raises(TypeError, match="candidate index must be an integer"):
        _service().candidate_at(
            build=_build(),
            seed=_seed(),
            potion_cooldown_seconds=10.0,
            starting_ultimate=0.0,
            index=True,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("potion_cooldown_seconds", "10", "potion cooldown must be numeric"),
        ("starting_ultimate", "0", "starting Ultimate must be numeric"),
        ("ultimate_generation_events", [], "ultimate_generation_events must be a tuple"),
        ("heroism_windows", [], "heroism_windows must be a tuple"),
        (
            "use_scheduled_combat_attacks_for_ultimate",
            1,
            "scheduled-combat Ultimate flag must be boolean",
        ),
    ),
)
def test_rotation_policy_frontier_rejects_coerced_runtime_inputs(
    field,
    value,
    message,
) -> None:
    kwargs = {
        "build": _build(),
        "seed": _seed(),
        "potion_cooldown_seconds": 10.0,
        "starting_ultimate": 0.0,
        "ultimate_generation_events": (),
        "heroism_windows": (),
        "use_scheduled_combat_attacks_for_ultimate": False,
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match=message):
        _service().frontier(**kwargs)
