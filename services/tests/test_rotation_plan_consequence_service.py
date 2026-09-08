from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import (
    AppliedResourceTimelineEvent,
    ResourceTimelineEventKind,
    ResourceTimelineResult,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_plan_consequence_service import (
    RotationPlanConsequenceService,
    RotationResourceConsequenceKind,
)


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def _sustain(*, ending: int, minimum: int, costs: tuple[tuple[str, int], ...], shortfall: int = 0):
    timeline = SimpleNamespace(
        starting_amount=31_109,
        ending_amount=ending,
        total_shortfall=shortfall,
        events=(SimpleNamespace(after=minimum),),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(
            timeline=timeline,
            action_cost_events=tuple(
                SimpleNamespace(source=source, amount=amount)
                for source, amount in costs
            ),
        ),
    )


def _timeline_sustain(
    *,
    starting: int,
    maximum: int,
    minimum: int,
    ending: int,
    wasted_restore: int = 0,
) -> SimpleNamespace:
    attempted_restore = max(0, ending - minimum) + int(wasted_restore)
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=starting,
        ending_amount=ending,
        starting_maximum=maximum,
        ending_maximum=maximum,
        events=(
            AppliedResourceTimelineEvent(
                time_seconds=2.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="test cost",
                before=starting,
                attempted_change=minimum - starting,
                applied_change=minimum - starting,
                after=minimum,
                maximum_before=maximum,
                maximum_after=maximum,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=4.0,
                kind=ResourceTimelineEventKind.RESTORATION,
                source="test restore",
                before=minimum,
                attempted_change=attempted_restore,
                applied_change=ending - minimum,
                after=ending,
                wasted_restore=int(wasted_restore),
                maximum_before=maximum,
                maximum_after=maximum,
            ),
        ),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
    )


def test_extra_expensive_cast_is_resource_worsened() -> None:
    baseline = _plan(
        RotationAction(39.0, 0, RotationActionKind.SKILL, "Illustrious Healing", "front"),
        RotationAction(60.0, 0, RotationActionKind.WAIT, None, "front"),
    )
    candidate = _plan(
        RotationAction(39.0, 0, RotationActionKind.SKILL, "Illustrious Healing", "front"),
        RotationAction(60.0, 0, RotationActionKind.SKILL, "Illustrious Healing", "front"),
    )

    result = RotationPlanConsequenceService().compare(
        baseline_plan=baseline,
        candidate_plan=candidate,
        baseline_sustain=_sustain(
            ending=21_853,
            minimum=14_361,
            costs=(("Illustrious Healing", 2_878),),
        ),
        candidate_sustain=_sustain(
            ending=18_975,
            minimum=13_838,
            costs=(("Illustrious Healing", 2_878), ("Illustrious Healing", 2_878)),
        ),
    )

    assert result.resource_kind is RotationResourceConsequenceKind.WORSENED
    assert result.total_cost_delta == 2_878
    assert result.minimum_resource_delta == -523
    assert result.ending_resource_delta == -2_878
    assert result.wait_delta == -1
    assert result.minimum_resource_fraction_delta is None
    assert result.ending_resource_fraction_delta is None
    assert result.wasted_restore_delta == 0
    assert [(item.name, item.delta) for item in result.cast_deltas] == [
        ("Illustrious Healing", 1),
    ]
    assert [(item.source, item.delta) for item in result.cost_deltas] == [
        ("Illustrious Healing", 2_878),
    ]


def test_cheaper_cast_substitution_is_resource_improved() -> None:
    baseline = _plan(
        RotationAction(40.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )
    candidate = _plan(
        RotationAction(40.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
    )

    result = RotationPlanConsequenceService().compare(
        baseline_plan=baseline,
        candidate_plan=candidate,
        baseline_sustain=_sustain(
            ending=21_853,
            minimum=14_361,
            costs=(("Combat Prayer", 3_764),),
        ),
        candidate_sustain=_sustain(
            ending=23_624,
            minimum=16_132,
            costs=(("Budding Seeds", 1_993),),
        ),
    )

    assert result.resource_kind is RotationResourceConsequenceKind.IMPROVED
    assert result.total_cost_delta == -1_771
    assert result.minimum_resource_delta == 1_771
    assert result.ending_resource_delta == 1_771
    assert {(item.name, item.delta) for item in result.cast_deltas} == {
        ("Budding Seeds", 1),
        ("Combat Prayer", -1),
    }
    assert {(item.source, item.delta) for item in result.cost_deltas} == {
        ("Budding Seeds", 1_993),
        ("Combat Prayer", -3_764),
    }


def test_shortfall_regression_is_resource_worsened_even_if_ending_resource_rises() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Emergency Heal", "front"),
    )

    result = RotationPlanConsequenceService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=_sustain(ending=10_000, minimum=5_000, costs=(), shortfall=0),
        candidate_sustain=_sustain(ending=12_000, minimum=6_000, costs=(), shortfall=500),
    )

    assert result.resource_kind is RotationResourceConsequenceKind.WORSENED
    assert result.shortfall_delta == 500


def test_consequence_exposes_normalized_resource_floor_without_changing_role_neutral_classification() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Role Neutral Skill", "front"),
    )

    result = RotationPlanConsequenceService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=_timeline_sustain(
            starting=24_000,
            maximum=30_000,
            minimum=12_000,
            ending=15_000,
        ),
        candidate_sustain=_timeline_sustain(
            starting=28_800,
            maximum=36_000,
            minimum=13_000,
            ending=18_000,
        ),
    )

    assert result.minimum_resource_delta == 1_000
    assert result.ending_resource_delta == 3_000
    assert result.resource_kind is RotationResourceConsequenceKind.IMPROVED
    assert result.baseline_minimum_resource_fraction == 0.4
    assert result.candidate_minimum_resource_fraction == 13_000 / 36_000
    assert result.minimum_resource_fraction_delta == (13_000 / 36_000) - 0.4
    assert result.baseline_ending_resource_fraction == 0.5
    assert result.candidate_ending_resource_fraction == 0.5
    assert result.ending_resource_fraction_delta == 0.0
    assert result.minimum_resource_fraction_delta < 0


def test_consequence_exposes_wasted_restore_without_changing_resource_classification() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Role Neutral Skill", "front"),
    )

    result = RotationPlanConsequenceService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=_timeline_sustain(
            starting=24_000,
            maximum=30_000,
            minimum=12_000,
            ending=18_000,
            wasted_restore=2_000,
        ),
        candidate_sustain=_timeline_sustain(
            starting=24_000,
            maximum=30_000,
            minimum=12_000,
            ending=18_000,
            wasted_restore=500,
        ),
    )

    assert result.resource_kind is RotationResourceConsequenceKind.NEUTRAL
    assert result.minimum_resource_delta == 0
    assert result.ending_resource_delta == 0
    assert result.baseline_wasted_restore == 2_000
    assert result.candidate_wasted_restore == 500
    assert result.wasted_restore_delta == -1_500
