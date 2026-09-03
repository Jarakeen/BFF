from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.build_candidate_context import BuildCandidateContextResult
from minmax.build_candidate_evaluator import evaluate_healing_candidate, rank_candidate_comparisons
from minmax.build_candidate_healing import ModeledHealingPotency
from minmax.build_candidate_sustain import BuildCandidateSustainComparison
from models.build_model import PlayerBuild
from services.encounter_provider_assignment import ProviderAssignment, ProviderAssignmentStatus
from services.encounter_provider_candidate import ProviderCandidate, ProviderCandidateStatus
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _provider(member_id: str) -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id="oaxiltso:coverage:war_horn",
        encounter_id="oaxiltso",
        requirement_type="war_horn",
        member_id=member_id,
        character_name=member_id.title(),
        build_name=f"{member_id.title()} Build",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("test",),
    )


def _assignment(primary_member_id: str) -> ProviderAssignment:
    return ProviderAssignment(
        requirement_id="oaxiltso:coverage:war_horn",
        encounter_id="oaxiltso",
        requirement_type="war_horn",
        status=ProviderAssignmentStatus.ASSIGNED,
        primary_providers=(_provider(primary_member_id),),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test assignment",
    )


def _capability_audit() -> SavedBuildCapabilityAudit:
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
    def audit_build(self, _build):
        return _capability_audit()


def _candidate(candidate_id: str, food: str) -> BuildCandidate:
    return BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id=candidate_id,
        candidate_build=PlayerBuild(
            Name="Magrat",
            BuildName="DF Healer",
            Food=food,
        ),
        changes=(
            BuildChange.from_values(
                path="Food",
                before="Baseline Food",
                after=food,
                source="phase12:test",
            ),
        ),
        candidate_source="phase12:test",
    )


def _sustain(candidate_context: BuildCandidateContextResult) -> BuildCandidateSustainComparison:
    return BuildCandidateSustainComparison(
        baseline_run=None,
        candidate_run=None,
        constraint=CandidateConstraint(
            name="magicka sustain",
            status=ConstraintStatus.PRESERVED,
            explanation="Candidate preserves modeled magicka sustain.",
        ),
    )


def test_higher_healing_candidate_is_blocked_when_provider_duty_is_reassigned(monkeypatch) -> None:
    safe = _candidate("food:safe", "Safe Food")
    greedy = _candidate("food:greedy", "Greedy Food")
    baseline_healing = ModeledHealingPotency(
        value=100.0,
        evaluated_skills=("Combat Prayer",),
    )
    baseline_assignments = (_assignment("magrat"),)

    def fake_healing(*, build, context, skill_names, tooltip_service):
        value = 125.0 if build.Food == "Greedy Food" else 110.0
        return ModeledHealingPotency(
            value=value,
            evaluated_skills=("Combat Prayer",),
        )

    monkeypatch.setattr(
        "minmax.build_candidate_evaluator.measure_modeled_healing_potency",
        fake_healing,
    )

    def resolve_context(candidate):
        return BuildCandidateContextResult(candidate=candidate, context=object())

    def resolve_assignments(build):
        if build.Food == "Greedy Food":
            return (_assignment("susan"),)
        return (_assignment("magrat"),)

    def evaluate(candidate):
        return evaluate_healing_candidate(
            candidate=candidate,
            baseline_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
            baseline_healing=baseline_healing,
            baseline_capability=_capability_audit(),
            baseline_assignments=baseline_assignments,
            member_id="magrat",
            healing_skill_names=("Combat Prayer",),
            tooltip_service=object(),
            capability_service=_CapabilityService(),
            resolve_context=resolve_context,
            resolve_sustain=_sustain,
            resolve_assignments=resolve_assignments,
        ).comparison

    safe_comparison = evaluate(safe)
    greedy_comparison = evaluate(greedy)
    ranking = rank_candidate_comparisons((greedy_comparison, safe_comparison))

    provider_constraint = next(
        constraint
        for constraint in greedy_comparison.constraints
        if constraint.name == "provider_responsibility"
    )
    assert greedy_comparison.candidate_value > safe_comparison.candidate_value
    assert provider_constraint.status is ConstraintStatus.WORSENED
    assert greedy_comparison.is_rankable is False
    assert ranking.ranked == (safe_comparison,)
    assert ranking.recommended is safe_comparison
