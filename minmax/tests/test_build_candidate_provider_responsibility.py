from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_capability import compare_provider_responsibilities
from minmax.build_candidate_comparison import BuildCandidateComparison, ConstraintStatus
from minmax.build_candidate_evaluator import rank_candidate_comparisons
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.encounter_provider_candidate import ProviderCandidate, ProviderCandidateStatus


def _provider(member_id: str, requirement_id: str = "oaxiltso:coverage:war_horn") -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id=requirement_id,
        encounter_id="oaxiltso",
        requirement_type="war_horn",
        member_id=member_id,
        character_name=member_id.title(),
        build_name=f"{member_id.title()} Build",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("test",),
    )


def _assignment(
    *,
    status: ProviderAssignmentStatus = ProviderAssignmentStatus.ASSIGNED,
    primary_member_ids: tuple[str, ...] = ("magrat",),
    requirement_id: str = "oaxiltso:coverage:war_horn",
) -> ProviderAssignment:
    return ProviderAssignment(
        requirement_id=requirement_id,
        encounter_id="oaxiltso",
        requirement_type="war_horn",
        status=status,
        primary_providers=tuple(_provider(member_id, requirement_id) for member_id in primary_member_ids),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test assignment",
    )


def _comparison(
    candidate_id: str,
    candidate_value: float,
    provider_constraint,
) -> BuildCandidateComparison:
    candidate = BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id=candidate_id,
        candidate_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        changes=(),
        candidate_source="phase12:test",
    )
    return BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=candidate_value,
        constraints=(provider_constraint,),
    )


def test_provider_responsibility_is_preserved_when_same_member_keeps_primary_duty() -> None:
    constraint = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=(_assignment(),),
        candidate_assignments=(_assignment(),),
    )

    assert constraint.name == "provider_responsibility"
    assert constraint.status is ConstraintStatus.PRESERVED
    assert "preserves every baseline primary provider responsibility" in constraint.explanation


def test_provider_responsibility_is_worsened_when_phase11_reassigns_primary_duty() -> None:
    constraint = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=(_assignment(),),
        candidate_assignments=(_assignment(primary_member_ids=("susan",)),),
    )

    assert constraint.status is ConstraintStatus.WORSENED
    assert "no longer owns assigned primary responsibility" in constraint.explanation
    assert "oaxiltso:coverage:war_horn" in constraint.explanation


def test_provider_responsibility_is_unknown_when_candidate_assignment_is_unresolved() -> None:
    constraint = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=(_assignment(),),
        candidate_assignments=(
            _assignment(
                status=ProviderAssignmentStatus.UNRESOLVED_CAPABILITY,
                primary_member_ids=(),
            ),
        ),
    )

    assert constraint.status is ConstraintStatus.UNKNOWN
    assert "responsibility is unresolved" in constraint.explanation


def test_provider_responsibility_is_unknown_when_candidate_assignment_row_is_missing() -> None:
    constraint = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=(_assignment(),),
        candidate_assignments=(),
    )

    assert constraint.status is ConstraintStatus.UNKNOWN
    assert "assignment evidence is missing" in constraint.explanation
    assert "oaxiltso:coverage:war_horn" in constraint.explanation


def test_provider_responsibility_is_worsened_when_assignment_becomes_insufficient() -> None:
    constraint = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=(_assignment(),),
        candidate_assignments=(
            _assignment(
                status=ProviderAssignmentStatus.INSUFFICIENT,
                primary_member_ids=(),
            ),
        ),
    )

    assert constraint.status is ConstraintStatus.WORSENED


def test_member_without_baseline_primary_duty_has_nothing_to_preserve() -> None:
    constraint = compare_provider_responsibilities(
        member_id="susan",
        baseline_assignments=(_assignment(primary_member_ids=("magrat",)),),
        candidate_assignments=(),
    )

    assert constraint.status is ConstraintStatus.PRESERVED
    assert "no assigned primary provider responsibilities" in constraint.explanation


def test_higher_damage_candidate_is_excluded_when_provider_duty_is_reassigned() -> None:
    baseline = (_assignment(),)
    preserved = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=baseline,
        candidate_assignments=(_assignment(),),
    )
    reassigned = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=baseline,
        candidate_assignments=(_assignment(primary_member_ids=("susan",)),),
    )
    eligible = _comparison("eligible", 110.0, preserved)
    blocked = _comparison("higher-damage-provider-loss", 125.0, reassigned)

    ranking = rank_candidate_comparisons((blocked, eligible))

    assert blocked.candidate_value > eligible.candidate_value
    assert blocked.is_rankable is False
    assert ranking.ranked == (eligible,)
    assert ranking.recommended is eligible
