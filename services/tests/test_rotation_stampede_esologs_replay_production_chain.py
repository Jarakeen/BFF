from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
)
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    RotationCandidatePeriodicDamageRuntimeProjectionService,
)
from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationPeriodicDamageTimingEntry,
    RotationPeriodicDamageTimingReport,
)
from services.rotation_dd_periodic_esologs_anchor_correlation_service import (
    RotationDDPeriodicEsoLogsCastImpactObservation,
)
from services.rotation_dd_periodic_esologs_replay_anchor_mapping_service import (
    RotationDDPeriodicEsoLogsReplayAnchorMappingService,
)
from services.rotation_dd_periodic_runtime_semantics_registry_service import (
    RotationDDPeriodicRuntimeSemanticsRegistryService,
)
from services.rotation_runtime_activation_anchor_evidence_service import (
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


def test_exact_esologs_stampede_impact_maps_through_runtime_projection() -> None:
    action = RotationAction(
        time_seconds=1.0,
        sequence=7,
        kind=RotationActionKind.SKILL,
        name="Stampede",
        bar="back",
    )
    plan = RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=6.0,
        actions=(action,),
    )
    observation = RotationDDPeriodicEsoLogsCastImpactObservation(
        skill_entity_id="stampede",
        report_code="R",
        fight_id=1,
        source_id=42,
        cast_event_index=10,
        cast_timestamp_ms=1000.0,
        cast_ability_id=39807,
        impact_event_index=11,
        impact_timestamp_ms=1300.0,
        impact_ability_id=38792,
        cast_track_id=9001,
        cast_track_linked=True,
    )

    mapped = RotationDDPeriodicEsoLogsReplayAnchorMappingService().map(
        plan=plan,
        observations=(observation,),
        replay_origin_timestamp_ms=0.0,
    )

    assert mapped.unresolved == ()
    assert len(mapped.evidence) == 1
    evidence = mapped.evidence[0]
    assert evidence.skill_entity_id == "stampede"
    assert evidence.action_time_seconds == 1.0
    assert evidence.action_sequence == 7
    assert evidence.anchor_time_seconds == 1.3
    assert "cast event 10 impact event 11" in evidence.source

    resolver_factory = RotationRuntimeActivationAnchorEvidenceService().resolver_factory(
        mapped.evidence
    )
    semantics = RotationDDPeriodicRuntimeSemanticsRegistryService().load()
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _StampedeTimingService(),  # type: ignore[arg-type]
        activation_anchor_resolver=resolver_factory(plan),
    ).project(
        plan=plan,
        semantics=semantics,
    )

    assert projection.resolved is True
    assert len(projection.entries) == 1
    assert tuple(event.time_seconds for event in projection.entries[0].events) == (
        2.3,
        3.3,
        4.3,
        5.3,
    )


def test_unlinked_esologs_stampede_impact_never_becomes_runtime_ticks() -> None:
    action = RotationAction(
        time_seconds=1.0,
        sequence=7,
        kind=RotationActionKind.SKILL,
        name="Stampede",
        bar="back",
    )
    plan = RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=6.0,
        actions=(action,),
    )
    observation = RotationDDPeriodicEsoLogsCastImpactObservation(
        skill_entity_id="stampede",
        report_code="R",
        fight_id=1,
        source_id=42,
        cast_event_index=10,
        cast_timestamp_ms=1000.0,
        cast_ability_id=39807,
        impact_event_index=11,
        impact_timestamp_ms=1300.0,
        impact_ability_id=38792,
        cast_track_id=9001,
        cast_track_linked=False,
    )

    mapped = RotationDDPeriodicEsoLogsReplayAnchorMappingService().map(
        plan=plan,
        observations=(observation,),
        replay_origin_timestamp_ms=0.0,
    )

    assert mapped.evidence == ()
    assert any("remains observational" in item for item in mapped.unresolved)

    resolver_factory = RotationRuntimeActivationAnchorEvidenceService().resolver_factory(
        mapped.evidence
    )
    projection = RotationCandidatePeriodicDamageRuntimeProjectionService(
        _StampedeTimingService(),  # type: ignore[arg-type]
        activation_anchor_resolver=resolver_factory(plan),
    ).project(
        plan=plan,
        semantics=RotationDDPeriodicRuntimeSemanticsRegistryService().load(),
    )

    assert projection.resolved is False
    assert projection.entries[0].events == ()
    assert "requires exact runtime anchor evidence" in projection.unresolved[0]
