from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
)
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
    PeriodicDamageMagnitudePolicy,
    RotationCandidatePeriodicDamageRuntimeProjectionService,
)
from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationPeriodicDamageTimingEntry,
    RotationPeriodicDamageTimingReport,
)
from services.rotation_dd_periodic_runtime_semantics_registry_service import (
    RotationDDPeriodicRuntimeSemanticsRegistryService,
)
from services.rotation_runtime_activation_anchor_evidence_service import (
    RotationRuntimeActivationAnchorEvidence,
    RotationRuntimeActivationAnchorEvidenceService,
)


class _StampedeTimingService:
    def inspect_action(self, action: RotationAction) -> RotationPeriodicDamageTimingReport:
        return RotationPeriodicDamageTimingReport(
            action=action,
            entries=(
                RotationPeriodicDamageTimingEntry(
                    source_name="Stampede",
                    coefficient_number=2,
                    skill_rank_id=1,
                    ability_id=1,
                    component_fragment="$2 Physical Damage every 1 second",
                    timing=SkillComponentRuntimeTiming(
                        interval_seconds=1.0,
                        bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
                        evidence="reviewed 1 second cadence",
                    ),
                    duration_seconds=15.0,
                    evidence=("reviewed Stampede timing",),
                ),
            ),
        )


def test_reviewed_stampede_registry_and_exact_impact_evidence_schedule_runtime_ticks() -> None:
    action = RotationAction(
        time_seconds=1.0,
        sequence=7,
        kind=RotationActionKind.SKILL,
        name="stampede",
        bar="back",
    )
    plan = RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=6.0,
        actions=(action,),
    )

    semantics = RotationDDPeriodicRuntimeSemanticsRegistryService().load()
    stampede = next(
        row
        for row in semantics
        if row.skill_entity_id == "stampede" and row.coefficient_number == 2
    )
    assert stampede.activation_anchor is PeriodicDamageActivationAnchor.IMPACT
    assert stampede.magnitude_policy is PeriodicDamageMagnitudePolicy.DYNAMIC_AT_TICK
    assert stampede.first_tick_offset_seconds == 1.0
    assert stampede.verified_interval_seconds == 1.0

    resolver_factory = RotationRuntimeActivationAnchorEvidenceService().resolver_factory(
        (
            RotationRuntimeActivationAnchorEvidence(
                skill_entity_id="stampede",
                action_time_seconds=1.0,
                action_sequence=7,
                activation_anchor=PeriodicDamageActivationAnchor.IMPACT,
                anchor_time_seconds=1.3,
                source="authoritative exact runtime impact event",
            ),
        )
    )

    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _StampedeTimingService(),  # type: ignore[arg-type]
        activation_anchor_resolver=resolver_factory(plan),
    ).project(
        plan=plan,
        semantics=semantics,
    )

    assert projection.resolved is True
    assert len(projection.entries) == 1
    entry = projection.entries[0]
    assert tuple(event.time_seconds for event in entry.events) == (
        2.3,
        3.3,
        4.3,
        5.3,
    )
    assert entry.active_end_time_seconds == 6.0
    assert any("activation anchor impact" in evidence for evidence in entry.evidence)
    assert any("magnitude policy dynamic_at_tick" in evidence for evidence in entry.evidence)


def test_prospective_stampede_preserves_impact_semantics_but_does_not_invent_ticks() -> None:
    action = RotationAction(
        time_seconds=1.0,
        sequence=7,
        kind=RotationActionKind.SKILL,
        name="stampede",
        bar="back",
    )
    plan = RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=6.0,
        actions=(action,),
    )

    semantics = RotationDDPeriodicRuntimeSemanticsRegistryService().load()
    stampede = next(
        row
        for row in semantics
        if row.skill_entity_id == "stampede" and row.coefficient_number == 2
    )
    assert stampede.activation_anchor is PeriodicDamageActivationAnchor.IMPACT
    assert stampede.first_tick_offset_seconds == 1.0
    assert stampede.verified_interval_seconds == 1.0

    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _StampedeTimingService(),  # type: ignore[arg-type]
        activation_anchor_resolver=None,
    ).project(
        plan=plan,
        semantics=semantics,
    )

    assert projection.resolved is False
    assert len(projection.entries) == 1
    assert projection.entries[0].events == ()
    assert projection.entries[0].active_end_time_seconds is None
    assert "reviewed activation anchor impact requires exact runtime anchor evidence" in projection.unresolved[0]


def test_stampede_runtime_chain_fails_closed_when_exact_impact_evidence_does_not_match_final_action() -> None:
    action = RotationAction(
        time_seconds=1.0,
        sequence=7,
        kind=RotationActionKind.SKILL,
        name="stampede",
        bar="back",
    )
    plan = RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=6.0,
        actions=(action,),
    )

    semantics = RotationDDPeriodicRuntimeSemanticsRegistryService().load()
    resolver_factory = RotationRuntimeActivationAnchorEvidenceService().resolver_factory(
        (
            RotationRuntimeActivationAnchorEvidence(
                skill_entity_id="stampede",
                action_time_seconds=1.0,
                action_sequence=6,
                activation_anchor=PeriodicDamageActivationAnchor.IMPACT,
                anchor_time_seconds=1.3,
                source="stale runtime impact event",
            ),
        )
    )

    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _StampedeTimingService(),  # type: ignore[arg-type]
        activation_anchor_resolver=resolver_factory(plan),
    ).project(
        plan=plan,
        semantics=semantics,
    )

    assert projection.resolved is False
    assert projection.entries[0].events == ()
    assert "requires exact runtime anchor evidence" in projection.unresolved[0]
