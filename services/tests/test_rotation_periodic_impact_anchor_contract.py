from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
)
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
    PeriodicDamageMagnitudePolicy,
    PeriodicDamageRefreshBoundary,
    RotationCandidatePeriodicDamageRuntimeProjectionService,
    RotationPeriodicDamageRuntimeSemantics,
)
from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationPeriodicDamageTimingEntry,
    RotationPeriodicDamageTimingReport,
)


class _ImpactPeriodicTimingService:
    def inspect_action(self, action: RotationAction) -> RotationPeriodicDamageTimingReport:
        return RotationPeriodicDamageTimingReport(
            action=action,
            entries=(
                RotationPeriodicDamageTimingEntry(
                    source_name="impact_periodic_skill",
                    coefficient_number=2,
                    skill_rank_id=1,
                    ability_id=1,
                    component_fragment="$2 Damage every 1 second",
                    timing=SkillComponentRuntimeTiming(
                        interval_seconds=1.0,
                        bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
                        evidence="reviewed generic impact-periodic cadence",
                    ),
                    duration_seconds=5.0,
                    evidence=("reviewed generic impact-periodic timing",),
                ),
            ),
        )


def _semantics() -> tuple[RotationPeriodicDamageRuntimeSemantics, ...]:
    return (
        RotationPeriodicDamageRuntimeSemantics(
            skill_entity_id="impact_periodic_skill",
            coefficient_number=2,
            first_tick_offset_seconds=1.0,
            refresh_boundary=PeriodicDamageRefreshBoundary.ALLOW_OLD_TICK_AT_RECAST,
            activation_anchor=PeriodicDamageActivationAnchor.IMPACT,
            magnitude_policy=PeriodicDamageMagnitudePolicy.DYNAMIC_AT_TICK,
            verified_interval_seconds=1.0,
            source="reviewed generic impact-anchor contract",
        ),
    )


def _plan(*actions: RotationAction, duration_seconds: float = 7.0) -> RotationPlan:
    return RotationPlan(
        character_name="Contract DD",
        build_name="Impact Anchor",
        duration_seconds=duration_seconds,
        actions=actions,
    )


def test_arbitrary_impact_anchored_periodic_skill_uses_exact_resolver_time() -> None:
    action = RotationAction(
        time_seconds=1.0,
        sequence=4,
        kind=RotationActionKind.SKILL,
        name="impact_periodic_skill",
        bar="back",
    )
    plan = _plan(action, duration_seconds=5.0)

    def resolve_anchor(candidate: RotationAction, anchor: PeriodicDamageActivationAnchor):
        assert candidate is action
        assert anchor is PeriodicDamageActivationAnchor.IMPACT
        return 1.4

    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _ImpactPeriodicTimingService(),  # type: ignore[arg-type]
        activation_anchor_resolver=resolve_anchor,
    ).project(plan=plan, semantics=_semantics())

    assert projection.resolved is True
    assert tuple(event.time_seconds for event in projection.entries[0].events) == (
        2.4,
        3.4,
        4.4,
    )


def test_arbitrary_impact_anchored_periodic_skill_fails_closed_without_resolver() -> None:
    action = RotationAction(
        time_seconds=1.0,
        sequence=4,
        kind=RotationActionKind.SKILL,
        name="impact_periodic_skill",
        bar="back",
    )
    plan = _plan(action, duration_seconds=5.0)

    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _ImpactPeriodicTimingService(),  # type: ignore[arg-type]
    ).project(plan=plan, semantics=_semantics())

    assert projection.resolved is False
    assert projection.entries[0].events == ()
    assert projection.entries[0].active_end_time_seconds is None
    assert "requires exact runtime anchor evidence" in projection.unresolved[0]


def test_impact_anchored_refresh_replaces_at_next_impact_not_next_cast() -> None:
    first = RotationAction(
        time_seconds=1.0,
        sequence=4,
        kind=RotationActionKind.SKILL,
        name="impact_periodic_skill",
        bar="back",
    )
    second = RotationAction(
        time_seconds=3.0,
        sequence=9,
        kind=RotationActionKind.SKILL,
        name="impact_periodic_skill",
        bar="back",
    )
    plan = _plan(first, second, duration_seconds=6.0)
    anchors = {
        (first.time_seconds, first.sequence): 1.2,
        (second.time_seconds, second.sequence): 3.2,
    }

    def resolve_anchor(action: RotationAction, anchor: PeriodicDamageActivationAnchor):
        assert anchor is PeriodicDamageActivationAnchor.IMPACT
        return anchors[(action.time_seconds, action.sequence)]

    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _ImpactPeriodicTimingService(),  # type: ignore[arg-type]
        activation_anchor_resolver=resolve_anchor,
    ).project(plan=plan, semantics=_semantics())

    assert projection.resolved is True
    first_entry, second_entry = projection.entries
    assert tuple(event.time_seconds for event in first_entry.events) == (2.2, 3.2)
    assert first_entry.active_end_time_seconds == 3.2
    assert tuple(event.time_seconds for event in second_entry.events) == (4.2, 5.2)
    assert second_entry.active_end_time_seconds == 6.0
