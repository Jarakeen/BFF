from __future__ import annotations

from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_dd_periodic_esologs_anchor_correlation_service import (
    RotationDDPeriodicEsoLogsCastImpactObservation,
)
from services.rotation_dd_periodic_esologs_replay_anchor_mapping_service import (
    RotationDDPeriodicEsoLogsReplayAnchorMappingService,
)
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
)


class _Generation:
    def __init__(self, plan: RotationPlan) -> None:
        self.plan = plan
        self.result = RotationGenerationResult(
            plan=plan,
            duration_evidence=SimpleNamespace(summary="replay seed"),
        )

    def generate_with_evidence(self, **kwargs):
        return self.result


class _CanonicalCandidates:
    def __init__(self) -> None:
        self.calls = []
        self.result = SimpleNamespace(validation="canonical-validation")

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_dashboard_forwards_exact_esologs_replay_anchor_evidence() -> None:
    plan = RotationPlan(
        character_name="Parse Cat",
        build_name="DD",
        duration_seconds=6.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=7,
                kind=RotationActionKind.SKILL,
                name="Stampede",
                bar="back",
            ),
        ),
    )
    mapped = RotationDDPeriodicEsoLogsReplayAnchorMappingService().map(
        plan=plan,
        observations=(
            RotationDDPeriodicEsoLogsCastImpactObservation(
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
            ),
        ),
        replay_origin_timestamp_ms=0.0,
    )
    assert mapped.unresolved == ()
    assert len(mapped.evidence) == 1

    build = PlayerBuild(Name="Parse Cat", BuildName="DD", Role="Damage Dealer")
    build.BackBarSkills = ["Stampede", "", "", "", "", ""]
    canonical = _CanonicalCandidates()
    support = RotationDashboardCanonicalCandidateSupport(
        generation=_Generation(plan),  # type: ignore[arg-type]
        canonical_candidates=canonical,  # type: ignore[arg-type]
    )
    request = RotationGenerationRequest(
        duration_seconds=6.0,
        ability_priorities=(
            AbilityPriorityEntry(
                bar="back",
                slot=1,
                skill_name="Stampede",
                priority=10,
            ),
        ),
        stabilize_recovery_heavies=True,
        recovery_pressure_resolver=lambda context: None,
    )

    support.run_effects(
        player_build=build,
        generation_request=request,
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=ResourceType.STAMINA,
        maximum_amount=30000,
        trigger_fraction=0.35,
        runtime_activation_anchor_evidence=mapped.evidence,
    )

    forwarded = canonical.calls[0]["runtime_activation_anchor_evidence"]
    assert forwarded == mapped.evidence
    assert forwarded[0].skill_entity_id == "stampede"
    assert forwarded[0].action_time_seconds == 1.0
    assert forwarded[0].action_sequence == 7
    assert forwarded[0].anchor_time_seconds == 1.3
    assert "ESO Logs report R fight 1" in forwarded[0].source
