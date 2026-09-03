from types import SimpleNamespace

from models.build_model import PlayerBuild

from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.build_candidate_context import BuildCandidateContextResult
from minmax.build_candidate_damage import ModeledDamagePotency
from minmax.build_candidate_evaluator import evaluate_damage_candidate, rank_candidate_comparisons
from minmax.build_candidate_sustain import BuildCandidateSustainComparison
from services.encounter_provider_assignment import ProviderAssignment, ProviderAssignmentStatus
from services.encounter_provider_candidate import ProviderCandidate, ProviderCandidateStatus
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _candidate(candidate_id: str) -> BuildCandidate:
    return BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id=candidate_id,
        candidate_build=PlayerBuild(BuildName="DF Healer", Mundus="The Apprentice"),
        changes=(
            BuildChange.from_values(
                path="Mundus",
                before="The Ritual",
                after="The Apprentice",
                source="test",
            ),
        ),
        candidate_source="test",
    )


def _audit() -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name="Magrat",
        build_name="DF Healer",
        character_id="magrat",
        resolved_sources=(),
        resolved_effects=(),
        conditional_sources=(),
        unresolved=(),
        capability_unresolved=(),
        boundaries=(),
    )


class _CapabilityService:
    def audit_build(self, build):
        return _audit()


def _sustain() -> BuildCandidateSustainComparison:
    return BuildCandidateSustainComparison(
        baseline_run=None,
        candidate_run=None,
        constraint=CandidateConstraint(
            name="magicka sustain",
            status=ConstraintStatus.PRESERVED,
            explanation="Candidate preserves the verified sustain requirement.",
        ),
        unresolved=(),
    )


def _provider(member_id: str) -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id="war-horn",
        encounter_id="oaxiltso-veteran",
        requirement_type="aggressive_horn",
        member_id=member_id,
        character_name="Magrat" if member_id == "magrat" else "Susan",
        build_name="DF Healer" if member_id == "magrat" else "Necro Tank",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("canonical:test",),
    )


def _assignment(
    status: ProviderAssignmentStatus,
    *,
    primary: tuple[ProviderCandidate, ...] = (),
) -> ProviderAssignment:
    return ProviderAssignment(
        requirement_id="war-horn",
        encounter_id="oaxiltso-veteran",
        requirement_type="aggressive_horn",
        status=status,
        primary_providers=primary,
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test assignment",
    )


def _evaluate(
    candidate_id: str,
    candidate_assignments: tuple[ProviderAssignment, ...],
):
    magrat = _provider("magrat")
    return evaluate_damage_candidate(
        candidate=_candidate(candidate_id),
        baseline_damage=ModeledDamagePotency(
            value=100.0,
            metric_name="single-event expected damage",
            evidence=("baseline canonical event = 100",),
        ),
        baseline_capability=_audit(),
        baseline_assignments=(
            _assignment(ProviderAssignmentStatus.ASSIGNED, primary=(magrat,)),
        ),
        member_id="magrat",
        capability_service=_CapabilityService(),
        resolve_context=lambda row: BuildCandidateContextResult(
            candidate=row,
            context=SimpleNamespace(),
            unresolved=(),
        ),
        resolve_damage=lambda context: ModeledDamagePotency(
            value=120.0,
            metric_name="single-event expected damage",
            evidence=("candidate canonical event = 120",),
        ),
        resolve_sustain=lambda context: _sustain(),
        resolve_assignments=lambda build: candidate_assignments,
    )


def test_damage_gain_is_rankable_when_provider_responsibility_is_preserved() -> None:
    magrat = _provider("magrat")
    result = _evaluate(
        "candidate-preserves-provider",
        (_assignment(ProviderAssignmentStatus.ASSIGNED, primary=(magrat,)),),
    )

    provider_constraint = result.comparison.constraints[-1]
    assert result.comparison.delta == 20.0
    assert provider_constraint.name == "provider_responsibility"
    assert provider_constraint.status is ConstraintStatus.PRESERVED
    assert result.comparison.is_rankable
    assert result.comparison.is_improvement


def test_higher_damage_candidate_is_blocked_when_primary_provider_duty_moves() -> None:
    susan = _provider("susan")
    result = _evaluate(
        "candidate-loses-provider",
        (_assignment(ProviderAssignmentStatus.ASSIGNED, primary=(susan,)),),
    )

    provider_constraint = result.comparison.constraints[-1]
    assert result.comparison.delta == 20.0
    assert provider_constraint.status is ConstraintStatus.WORSENED
    assert "war-horn" in provider_constraint.explanation
    assert not result.comparison.is_rankable
    assert not result.comparison.is_improvement


def test_higher_damage_candidate_is_blocked_when_provider_duty_becomes_unresolved() -> None:
    result = _evaluate(
        "candidate-provider-unknown",
        (_assignment(ProviderAssignmentStatus.UNRESOLVED_CAPABILITY),),
    )

    provider_constraint = result.comparison.constraints[-1]
    assert result.comparison.delta == 20.0
    assert provider_constraint.status is ConstraintStatus.UNKNOWN
    assert "war-horn" in provider_constraint.explanation
    assert not result.comparison.is_rankable


def test_missing_candidate_assignment_evidence_is_unknown_not_silently_preserved() -> None:
    result = _evaluate("candidate-provider-missing", ())

    provider_constraint = result.comparison.constraints[-1]
    assert result.comparison.delta == 20.0
    assert provider_constraint.status is ConstraintStatus.UNKNOWN
    assert "war-horn" in provider_constraint.explanation
    assert not result.comparison.is_rankable


def test_ranking_prefers_lower_damage_candidate_that_preserves_provider_duty() -> None:
    magrat = _provider("magrat")
    susan = _provider("susan")

    safe = _evaluate(
        "candidate-safe",
        (_assignment(ProviderAssignmentStatus.ASSIGNED, primary=(magrat,)),),
    ).comparison
    unsafe = _evaluate(
        "candidate-unsafe",
        (_assignment(ProviderAssignmentStatus.ASSIGNED, primary=(susan,)),),
    ).comparison

    ranking = rank_candidate_comparisons((unsafe, safe))

    assert unsafe.delta == safe.delta == 20.0
    assert not unsafe.is_rankable
    assert safe.is_rankable
    assert ranking.ranked == (safe,)
    assert ranking.recommended is safe
