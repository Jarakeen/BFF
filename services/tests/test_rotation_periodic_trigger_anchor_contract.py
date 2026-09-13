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


class _ScaldingRuneTimingService:
    def inspect_action(self, action: RotationAction) -> RotationPeriodicDamageTimingReport:
        return RotationPeriodicDamageTimingReport(
            action=action,
            entries=(
                RotationPeriodicDamageTimingEntry(
                    source_name="Scalding Rune",
                    coefficient_number=2,
                    skill_rank_id=10,
                    ability_id=20,
                    component_fragment="$2 Flame Damage every 2 seconds",
                    timing=SkillComponentRuntimeTiming(
                        interval_seconds=2.0,
                        bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
                        evidence="reviewed 2-second cadence for contract test",
                    ),
                    duration_seconds=22.0,
                    evidence=("reviewed trigger-anchor contract test",),
                ),
            ),
        )


def _action(time_seconds: float, sequence: int) -> RotationAction:
    return RotationAction(
        time_seconds,
        sequence,
        RotationActionKind.SKILL,
        name="scalding_rune",
        bar="front",
    )


def _plan(*actions: RotationAction, duration: float = 30.0) -> RotationPlan:
    return RotationPlan(
        character_name="Test",
        build_name="DD",
        duration_seconds=duration,
        actions=tuple(actions),
    )


def _semantics() -> RotationPeriodicDamageRuntimeSemantics:
    return RotationPeriodicDamageRuntimeSemantics(
        skill_entity_id="scalding_rune",
        coefficient_number=2,
        first_tick_offset_seconds=2.0,
        refresh_boundary=PeriodicDamageRefreshBoundary.REPLACE_BEFORE_RECAST_TICK,
        source="reviewed trigger-anchor contract test",
        verified_interval_seconds=2.0,
        activation_anchor=PeriodicDamageActivationAnchor.TRIGGER,
    )


def test_trigger_anchor_fails_closed_without_exact_runtime_trigger() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _ScaldingRuneTimingService()
    ).project(
        plan=_plan(_action(0.0, 0), duration=30.0),
        semantics=(_semantics(),),
    )

    assert projection.resolved is False
    assert projection.entries[0].events == ()
    assert (
        "activation anchor trigger requires exact runtime anchor evidence"
        in projection.unresolved[0]
    )


def test_trigger_anchor_uses_trigger_time_and_refreshes_at_next_trigger_not_cast() -> None:
    trigger_times = {0: 4.0, 1: 14.5}
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _ScaldingRuneTimingService(),
        activation_anchor_resolver=lambda action, anchor: (
            trigger_times[action.sequence]
            if anchor is PeriodicDamageActivationAnchor.TRIGGER
            else action.time_seconds
        ),
    ).project(
        plan=_plan(_action(0.0, 0), _action(10.0, 1), duration=30.0),
        semantics=(_semantics(),),
    )

    assert projection.resolved is True
    assert tuple(event.time_seconds for event in projection.entries[0].events) == (
        6.0,
        8.0,
        10.0,
        12.0,
        14.0,
    )
    assert projection.entries[0].active_end_time_seconds == 14.5
    assert tuple(event.time_seconds for event in projection.entries[1].events) == (
        16.5,
        18.5,
        20.5,
        22.5,
        24.5,
        26.5,
        28.5,
    )
    assert projection.entries[1].active_end_time_seconds == 30.0
    assert (
        "activation anchor trigger from reviewed trigger-anchor contract test"
        in projection.entries[0].evidence
    )


def test_trigger_refresh_fails_closed_when_next_trigger_is_unknown() -> None:
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _ScaldingRuneTimingService(),
        activation_anchor_resolver=lambda action, anchor: (
            4.0
            if anchor is PeriodicDamageActivationAnchor.TRIGGER and action.sequence == 0
            else None
        ),
    ).project(
        plan=_plan(_action(0.0, 0), _action(10.0, 1), duration=30.0),
        semantics=(_semantics(),),
    )

    assert projection.resolved is False
    assert projection.entries[0].events == ()
    assert (
        "next trigger refresh anchor requires exact runtime anchor evidence"
        in projection.unresolved[0]
    )
