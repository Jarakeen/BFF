from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
)
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
    PeriodicDamageRefreshBoundary,
    RotationCandidatePeriodicDamageRuntimeProjectionService,
    RotationPeriodicDamageRuntimeSemantics,
)
from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationPeriodicDamageTimingEntry,
    RotationPeriodicDamageTimingReport,
)


class _TimingService:
    def __init__(self, *, interval_seconds: float = 2.0, duration_seconds: float = 10.0):
        self.interval_seconds = interval_seconds
        self.duration_seconds = duration_seconds

    def inspect_action(self, action: RotationAction) -> RotationPeriodicDamageTimingReport:
        return RotationPeriodicDamageTimingReport(
            action=action,
            entries=(
                RotationPeriodicDamageTimingEntry(
                    source_name="Burning Talons",
                    coefficient_number=2,
                    skill_rank_id=10,
                    ability_id=20,
                    component_fragment="$2 Flame Damage every 2 seconds",
                    timing=SkillComponentRuntimeTiming(
                        interval_seconds=self.interval_seconds,
                        bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
                        evidence="every 2 seconds",
                    ),
                    duration_seconds=self.duration_seconds,
                    evidence=("reviewed cadence",),
                ),
            ),
        )


def _action(
    time_seconds: float,
    sequence: int = 0,
    *,
    kind: RotationActionKind = RotationActionKind.SKILL,
) -> RotationAction:
    return RotationAction(
        time_seconds,
        sequence,
        kind,
        name="burning_talons",
        bar="front",
    )


def _plan(*actions: RotationAction, duration: float = 10.0) -> RotationPlan:
    return RotationPlan(
        character_name="Test",
        build_name="DD",
        duration_seconds=duration,
        actions=tuple(actions),
    )


def _semantics(
    *,
    first_tick: float = 2.0,
    boundary: PeriodicDamageRefreshBoundary = PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK,
    anchor: PeriodicDamageActivationAnchor = PeriodicDamageActivationAnchor.CAST,
) -> RotationPeriodicDamageRuntimeSemantics:
    return RotationPeriodicDamageRuntimeSemantics(
        skill_entity_id="burning_talons",
        coefficient_number=2,
        first_tick_offset_seconds=first_tick,
        refresh_boundary=boundary,
        source="reviewed U50 runtime evidence",
        activation_anchor=anchor,
    )


def test_recast_clips_old_periodic_instance_before_later_ticks() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService()
    ).project(
        plan=_plan(_action(0.0), _action(5.0), duration=10.0),
        semantics=(_semantics(),),
    )

    assert projection.resolved is True
    assert len(projection.entries) == 2
    assert tuple(event.time_seconds for event in projection.entries[0].events) == (2.0, 4.0)
    assert tuple(event.time_seconds for event in projection.entries[1].events) == (7.0, 9.0)
    assert projection.entries[0].active_end_time_seconds == 5.0
    assert projection.entries[1].active_end_time_seconds == 10.0


def test_ultimate_parent_projects_and_refreshes_periodic_ticks() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService()
    ).project(
        plan=_plan(
            _action(0.0, 0, kind=RotationActionKind.ULTIMATE),
            _action(5.0, 1, kind=RotationActionKind.ULTIMATE),
            duration=10.0,
        ),
        semantics=(_semantics(),),
    )

    assert projection.resolved is True
    assert len(projection.entries) == 2
    assert all(entry.action.kind is RotationActionKind.ULTIMATE for entry in projection.entries)
    assert tuple(event.time_seconds for event in projection.entries[0].events) == (2.0, 4.0)
    assert tuple(event.time_seconds for event in projection.entries[1].events) == (7.0, 9.0)
    assert projection.entries[0].active_end_time_seconds == 5.0


def test_exact_recast_boundary_can_explicitly_allow_old_tick() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService(interval_seconds=5.0)
    ).project(
        plan=_plan(_action(0.0), _action(5.0), duration=10.0),
        semantics=(
            _semantics(
                first_tick=5.0,
                boundary=PeriodicDamageRefreshBoundary.ALLOW_OLD_TICK_AT_RECAST,
            ),
        ),
    )

    assert projection.resolved is True
    assert tuple(event.time_seconds for event in projection.entries[0].events) == (5.0,)
    assert tuple(event.time_seconds for event in projection.entries[1].events) == (10.0,)


def test_exact_recast_boundary_is_excluded_when_recast_replaces_first() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService(interval_seconds=5.0)
    ).project(
        plan=_plan(_action(0.0), _action(5.0), duration=10.0),
        semantics=(_semantics(first_tick=5.0),),
    )

    assert projection.resolved is True
    assert projection.entries[0].events == ()
    assert tuple(event.time_seconds for event in projection.entries[1].events) == (10.0,)


def test_plan_horizon_clips_periodic_ticks_without_ghost_damage() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService()
    ).project(
        plan=_plan(_action(8.0), duration=10.0),
        semantics=(_semantics(),),
    )

    assert projection.resolved is True
    assert tuple(event.time_seconds for event in projection.entries[0].events) == (10.0,)
    assert projection.entries[0].active_end_time_seconds == 10.0


def test_impact_anchor_fails_closed_without_exact_runtime_anchor() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService(interval_seconds=1.0, duration_seconds=4.0)
    ).project(
        plan=_plan(_action(0.0), duration=10.0),
        semantics=(
            _semantics(
                first_tick=1.0,
                anchor=PeriodicDamageActivationAnchor.IMPACT,
            ),
        ),
    )

    assert projection.resolved is False
    assert projection.entries[0].events == ()
    assert "activation anchor impact requires exact runtime anchor evidence" in projection.unresolved[0]


def test_impact_anchor_uses_resolved_impact_time_for_duration_and_ticks() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService(interval_seconds=1.0, duration_seconds=4.0),
        activation_anchor_resolver=lambda action, anchor: (
            action.time_seconds + 0.25
            if anchor is PeriodicDamageActivationAnchor.IMPACT
            else action.time_seconds
        ),
    ).project(
        plan=_plan(_action(1.0), duration=10.0),
        semantics=(
            _semantics(
                first_tick=1.0,
                anchor=PeriodicDamageActivationAnchor.IMPACT,
            ),
        ),
    )

    assert projection.resolved is True
    assert tuple(event.time_seconds for event in projection.entries[0].events) == (
        2.25,
        3.25,
        4.25,
        5.25,
    )
    assert projection.entries[0].active_end_time_seconds == 5.25
    assert "activation anchor impact from reviewed U50 runtime evidence" in projection.entries[0].evidence


def test_impact_anchored_refresh_uses_next_impact_not_next_cast() -> None:
    impacts = {0: 0.5, 1: 5.8}
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService(interval_seconds=2.0, duration_seconds=10.0),
        activation_anchor_resolver=lambda action, anchor: (
            impacts[action.sequence]
            if anchor is PeriodicDamageActivationAnchor.IMPACT
            else action.time_seconds
        ),
    ).project(
        plan=_plan(_action(0.0, 0), _action(5.0, 1), duration=10.0),
        semantics=(
            _semantics(
                first_tick=1.0,
                anchor=PeriodicDamageActivationAnchor.IMPACT,
            ),
        ),
    )

    assert projection.resolved is True
    assert tuple(event.time_seconds for event in projection.entries[0].events) == (
        1.5,
        3.5,
        5.5,
    )
    assert projection.entries[0].active_end_time_seconds == 5.8
    assert tuple(event.time_seconds for event in projection.entries[1].events) == (
        6.8,
        8.8,
    )


def test_impact_anchored_refresh_fails_closed_when_next_impact_is_unknown() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService(interval_seconds=1.0, duration_seconds=10.0),
        activation_anchor_resolver=lambda action, anchor: (
            0.25
            if anchor is PeriodicDamageActivationAnchor.IMPACT and action.sequence == 0
            else None
        ),
    ).project(
        plan=_plan(_action(0.0, 0), _action(5.0, 1), duration=10.0),
        semantics=(
            _semantics(
                first_tick=1.0,
                anchor=PeriodicDamageActivationAnchor.IMPACT,
            ),
        ),
    )

    assert projection.resolved is False
    assert projection.entries[0].events == ()
    assert "next impact refresh anchor requires exact runtime anchor evidence" in projection.unresolved[0]


def test_missing_reviewed_runtime_semantics_fail_closed() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _TimingService()
    ).project(
        plan=_plan(_action(0.0), duration=10.0),
        semantics=(),
    )

    assert projection.resolved is False
    assert projection.entries[0].events == ()
    assert "reviewed first-tick/refresh semantics are unavailable" in projection.unresolved[0]


def test_semantics_require_provenance() -> None:
    try:
        RotationPeriodicDamageRuntimeSemantics(
            skill_entity_id="burning_talons",
            coefficient_number=2,
            first_tick_offset_seconds=2.0,
            refresh_boundary=PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK,
            source="",
        )
    except ValueError as exc:
        assert "require provenance" in str(exc)
    else:
        raise AssertionError("missing provenance should fail closed")
