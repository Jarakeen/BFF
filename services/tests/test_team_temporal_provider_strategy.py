from __future__ import annotations

from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.named_buff_resolution_service import NamedBuffContribution
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_candidate_ranking import PrescribedSlotCandidateEvidence
from services.team_prescription_optimizer import optimize_prescribed_roster_candidates
from services.team_provider_temporal_coverage_service import (
    TeamProviderTemporalCoverageService,
    TeamProviderTemporalRequirement,
    TeamProviderTimedApplication,
)


def _effect(source):
    return NamedBuffContribution(
        stacking_key="major_force",
        objective_key="critical_damage",
        projected_delta=0.20,
        source=source,
        source_kind="skill",
    )


def _evidence(candidate_id, *, role, value, horn=False):
    build = PlayerBuild(
        Name=candidate_id,
        BuildName=f"{candidate_id} Build",
        Role=role,
        EsoClass="Templar",
    )
    candidate = BuildCandidate.from_build(
        character_id=f"candidate:{candidate_id}",
        baseline_build_id="temporal-provider-baseline",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(),
        candidate_source="phase13.2:test-temporal-provider-strategy",
    )
    comparison = BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=value,
        constraints=(
            CandidateConstraint(
                name="hard constraint",
                status=ConstraintStatus.PRESERVED,
                explanation="temporal provider strategy test",
            ),
        ),
    )
    return PrescribedSlotCandidateEvidence(
        comparison=comparison,
        provider_requirement_ids=("aggressive_horn",) if horn else (),
        provider_effects=(_effect(f"{candidate_id} Horn"),) if horn else (),
    )


def _roster():
    return PrescribedRoster(
        name="Timed Provider Roster",
        goal="Burn Window",
        scope=TeamPrescriptionScope(
            dimensions=(PrescriptionDimension.CLASS, PrescriptionDimension.BUILD)
        ),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Main Tank",
                player_name=None,
                source_build_name=None,
                prescribed_role="Tank",
                unresolved=("Main Tank open",),
            ),
            PrescribedRosterAssignment(
                slot_name="Healer 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="Healer",
                unresolved=("Healer 1 open",),
            ),
        ),
        unresolved=("Main Tank open", "Healer 1 open"),
    )


def test_hard_strategy_can_require_two_duplicate_named_buff_carriers():
    result = optimize_prescribed_roster_candidates(
        roster=_roster(),
        provider_requirements_by_slot={
            "Main Tank": ("aggressive_horn",),
            "Healer 1": ("aggressive_horn",),
        },
        candidate_pools={
            "Main Tank": (
                _evidence("tank-raw", role="Tank", value=150.0, horn=False),
                _evidence("tank-horn", role="Tank", value=125.0, horn=True),
            ),
            "Healer 1": (
                _evidence("healer-raw", role="Healer", value=150.0, horn=False),
                _evidence("healer-horn", role="Healer", value=125.0, horn=True),
            ),
        },
    )

    assert result.applied_count == 2
    assert result.final_roster.assignments[0].source_build_name == "tank-horn Build"
    assert result.final_roster.assignments[1].source_build_name == "healer-horn Build"


def test_selected_tank_and_healer_horns_can_be_staggered_through_burn_window():
    coverage = TeamProviderTemporalCoverageService.evaluate(
        TeamProviderTemporalRequirement(
            effect_key="major_force",
            start_seconds=0.0,
            end_seconds=20.0,
            label="hard burn",
            minimum_distinct_sources=2,
        ),
        applications=(
            TeamProviderTimedApplication(
                effect_key="major_force",
                source="Main Tank Horn",
                start_seconds=0.0,
                duration_seconds=10.0,
            ),
            TeamProviderTimedApplication(
                effect_key="major_force",
                source="Healer Horn",
                start_seconds=10.0,
                duration_seconds=10.0,
            ),
        ),
    )

    assert coverage.full_requirement_met is True
    assert coverage.distinct_source_count == 2
    assert coverage.simultaneous_overlap_seconds == 0.0


def test_firing_both_horns_together_fails_same_twenty_second_burn_plan():
    coverage = TeamProviderTemporalCoverageService.evaluate(
        TeamProviderTemporalRequirement(
            effect_key="major_force",
            start_seconds=0.0,
            end_seconds=20.0,
            label="hard burn",
            minimum_distinct_sources=2,
        ),
        applications=(
            TeamProviderTimedApplication(
                effect_key="major_force",
                source="Main Tank Horn",
                start_seconds=0.0,
                duration_seconds=10.0,
            ),
            TeamProviderTimedApplication(
                effect_key="major_force",
                source="Healer Horn",
                start_seconds=0.0,
                duration_seconds=10.0,
            ),
        ),
    )

    assert coverage.distinct_source_requirement_met is True
    assert coverage.full_window_covered is False
    assert coverage.full_requirement_met is False
    assert coverage.simultaneous_overlap_seconds == 10.0
    assert coverage.uncovered_intervals == ((10.0, 20.0),)
