from types import SimpleNamespace

from models.build_model import PlayerBuild

from minmax.build_candidate import (
    BuildCandidate,
    BuildChange,
    CandidateEvaluationState,
)
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.build_candidate_context import BuildCandidateContextResult
from minmax.build_candidate_evaluator import (
    evaluate_damage_candidate,
    evaluate_healing_candidate,
    rank_candidate_comparisons,
)
from minmax.build_candidate_damage import ModeledDamagePotency
from minmax.build_candidate_healing import ModeledHealingPotency
from minmax.build_candidate_sustain import BuildCandidateSustainComparison
from minmax.evaluation_objective import EvaluationObjective
from minmax.skill_component_classification import SkillEffectKind
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _candidate(
    candidate_id: str,
    *,
    state: CandidateEvaluationState = CandidateEvaluationState.EVALUABLE,
    unresolved: tuple[str, ...] = (),
) -> BuildCandidate:
    build = PlayerBuild(BuildName="DF Healer", Mundus="The Ritual")
    return BuildCandidate.from_build(
        character_id="magrat",
        baseline_build_id="df-healer",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(
            BuildChange.from_values(
                path="Mundus",
                before="The Mage",
                after="The Ritual",
                source="test",
            ),
        ),
        candidate_source="test",
        evaluation_state=state,
        unresolved=unresolved,
    )


def _audit(*, unresolved: tuple[str, ...] = ()) -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name="Magrat",
        build_name="DF Healer",
        character_id="magrat",
        resolved_sources=(),
        resolved_effects=(),
        conditional_sources=(),
        unresolved=unresolved,
        capability_unresolved=unresolved,
        boundaries=(),
    )


class _CapabilityService:
    def __init__(self, audit):
        self.audit = audit
        self.calls = []

    def audit_build(self, build):
        self.calls.append(build)
        return self.audit


class _Coefficients:
    def resolve_name(self, name):
        return SimpleNamespace(
            rank=SimpleNamespace(entity_id="combat_prayer"),
            unresolved=(),
        )


class _Components:
    def get_for_skill_rank(self, skill_rank_id):
        return (
            SimpleNamespace(
                coefficient_number=1,
                effect_kind=SkillEffectKind.HEAL,
            ),
        )


class _TooltipService:
    def __init__(self, value: float):
        self.coefficients = _Coefficients()
        self.components = _Components()
        self.value = value

    def evaluate_entity_id(self, *, build, context, entity_id):
        return SimpleNamespace(
            skill=SimpleNamespace(
                name="Combat Prayer",
                entity_id=entity_id,
                skill_rank_id=123,
            ),
            components=(
                SimpleNamespace(coefficient_number=1, final_value=self.value),
            ),
            component_actual_effect_trace=(),
            unresolved=(),
        )


def _sustain(
    status: ConstraintStatus = ConstraintStatus.PRESERVED,
    *,
    unresolved: tuple[str, ...] = (),
) -> BuildCandidateSustainComparison:
    return BuildCandidateSustainComparison(
        baseline_run=None,
        candidate_run=None,
        constraint=CandidateConstraint(
            name="magicka sustain",
            status=status,
            explanation=f"sustain is {status.value}",
        ),
        unresolved=unresolved,
    )


def test_evaluate_healing_candidate_combines_objective_and_hard_constraints() -> None:
    candidate = _candidate("df-healer:mundus:ritual")
    capability_service = _CapabilityService(_audit())

    result = evaluate_healing_candidate(
        candidate=candidate,
        baseline_build=PlayerBuild(BuildName="DF Healer", Mundus="The Mage"),
        baseline_healing=ModeledHealingPotency(
            value=100.0,
            evaluated_skills=("Combat Prayer",),
            evidence=("baseline heal 100",),
        ),
        baseline_capability=_audit(),
        baseline_assignments=(),
        member_id="magrat",
        healing_skill_names=("Combat Prayer",),
        tooltip_service=_TooltipService(112.0),
        capability_service=capability_service,
        resolve_context=lambda row: BuildCandidateContextResult(
            candidate=row,
            context=object(),
            unresolved=(),
        ),
        resolve_sustain=lambda context: _sustain(),
        resolve_assignments=lambda build: (),
    )

    assert result.comparison.baseline_value == 100.0
    assert result.comparison.candidate_value == 112.0
    assert result.comparison.delta == 12.0
    assert result.comparison.is_rankable
    assert result.comparison.is_improvement
    assert [row.name for row in result.comparison.constraints] == [
        "magicka sustain",
        "capability_coverage",
        "provider_responsibility",
    ]
    assert len(capability_service.calls) == 1


def test_context_diagnostic_does_not_universally_block_resolved_evaluators() -> None:
    candidate = _candidate("df-healer:mundus:ritual")

    result = evaluate_healing_candidate(
        candidate=candidate,
        baseline_build=PlayerBuild(BuildName="DF Healer"),
        baseline_healing=ModeledHealingPotency(
            value=100.0,
            evaluated_skills=("Combat Prayer",),
        ),
        baseline_capability=_audit(),
        baseline_assignments=(),
        member_id="magrat",
        healing_skill_names=("Combat Prayer",),
        tooltip_service=_TooltipService(112.0),
        capability_service=_CapabilityService(_audit()),
        resolve_context=lambda row: BuildCandidateContextResult(
            candidate=row,
            context=object(),
            unresolved=("Passive rank is not recorded for character: Frozen Armor",),
        ),
        resolve_sustain=lambda context: _sustain(),
        resolve_assignments=lambda build: (),
    )

    assert result.comparison.delta == 12.0
    assert result.comparison.is_rankable
    assert "Frozen Armor" not in " ".join(result.comparison.unresolved)


def test_evaluate_healing_candidate_keeps_unresolved_sustain_unrankable() -> None:
    candidate = _candidate("df-healer:mundus:ritual")

    result = evaluate_healing_candidate(
        candidate=candidate,
        baseline_build=PlayerBuild(BuildName="DF Healer"),
        baseline_healing=ModeledHealingPotency(
            value=100.0,
            evaluated_skills=("Combat Prayer",),
        ),
        baseline_capability=_audit(),
        baseline_assignments=(),
        member_id="magrat",
        healing_skill_names=("Combat Prayer",),
        tooltip_service=_TooltipService(112.0),
        capability_service=_CapabilityService(_audit()),
        resolve_context=lambda row: BuildCandidateContextResult(
            candidate=row,
            context=object(),
            unresolved=(),
        ),
        resolve_sustain=lambda context: _sustain(
            ConstraintStatus.UNKNOWN,
            unresolved=("action plan unresolved",),
        ),
        resolve_assignments=lambda build: (),
    )

    assert result.comparison.delta == 12.0
    assert not result.comparison.is_rankable
    assert "action plan unresolved" in result.comparison.unresolved


def test_non_evaluable_candidate_does_not_call_downstream_resolvers() -> None:
    candidate = _candidate(
        "df-healer:mundus:unknown",
        state=CandidateEvaluationState.UNKNOWN,
        unresolved=("Mundus effect unresolved",),
    )
    calls = []

    def should_not_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("downstream resolver should not run")

    result = evaluate_healing_candidate(
        candidate=candidate,
        baseline_build=PlayerBuild(BuildName="DF Healer"),
        baseline_healing=ModeledHealingPotency(
            value=100.0,
            evaluated_skills=("Combat Prayer",),
        ),
        baseline_capability=_audit(),
        baseline_assignments=(),
        member_id="magrat",
        healing_skill_names=("Combat Prayer",),
        tooltip_service=_TooltipService(112.0),
        capability_service=SimpleNamespace(audit_build=should_not_run),
        resolve_context=should_not_run,
        resolve_sustain=should_not_run,
        resolve_assignments=should_not_run,
    )

    assert not calls
    assert not result.comparison.is_rankable
    assert result.comparison.rejection_reason == "Candidate is not evaluable: unknown"
    assert result.comparison.unresolved == ("Mundus effect unresolved",)


def _comparison(candidate_id: str, delta: float, *, rankable: bool = True) -> BuildCandidateComparison:
    candidate = _candidate(candidate_id)
    constraints = (
        CandidateConstraint(
            name="sustain",
            status=ConstraintStatus.PRESERVED if rankable else ConstraintStatus.UNKNOWN,
            explanation="test constraint",
        ),
    )
    return BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.HEALING,
        baseline_value=100.0,
        candidate_value=100.0 + delta,
        constraints=constraints,
    )


def test_candidate_ranking_is_deterministic_and_excludes_blocked_candidates() -> None:
    blocked = _comparison("candidate-z", 50.0, rankable=False)
    tied_b = _comparison("candidate-b", 10.0)
    best = _comparison("candidate-c", 20.0)
    tied_a = _comparison("candidate-a", 10.0)

    result = rank_candidate_comparisons((blocked, tied_b, best, tied_a))

    assert [row.candidate.candidate_id for row in result.ranked] == [
        "candidate-c",
        "candidate-a",
        "candidate-b",
    ]
    assert result.recommended is best


def test_evaluate_damage_candidate_uses_authoritative_metric_and_constraints() -> None:
    candidate = _candidate("dd:mundus:thief")
    capability_service = _CapabilityService(_audit())

    result = evaluate_damage_candidate(
        candidate=candidate,
        baseline_damage=ModeledDamagePotency(
            value=100.0,
            metric_name="single-event expected damage",
            evidence=("baseline canonical DD event = 100",),
        ),
        baseline_capability=_audit(),
        baseline_assignments=(),
        member_id="dd-1",
        capability_service=capability_service,
        resolve_context=lambda row: BuildCandidateContextResult(
            candidate=row,
            context=object(),
            unresolved=(),
        ),
        resolve_damage=lambda context: ModeledDamagePotency(
            value=112.0,
            metric_name="single-event expected damage",
            evidence=("candidate canonical DD event = 112",),
        ),
        resolve_sustain=lambda context: _sustain(),
        resolve_assignments=lambda build: (),
    )

    assert result.comparison.objective is EvaluationObjective.DAMAGE
    assert result.comparison.baseline_value == 100.0
    assert result.comparison.candidate_value == 112.0
    assert result.comparison.delta == 12.0
    assert result.comparison.is_rankable
    assert result.comparison.is_improvement
    assert [row.name for row in result.comparison.constraints] == [
        "magicka sustain",
        "capability_coverage",
        "provider_responsibility",
    ]
    assert result.comparison.evidence == (
        "baseline: baseline canonical DD event = 100",
        "candidate: candidate canonical DD event = 112",
    )


def test_damage_candidate_does_not_call_metric_a_raid_dps_ceiling() -> None:
    result = evaluate_damage_candidate(
        candidate=_candidate("dd:mundus:thief"),
        baseline_damage=ModeledDamagePotency(
            value=100.0,
            metric_name="single-event expected damage",
        ),
        baseline_capability=_audit(),
        baseline_assignments=None,
        member_id="dd-1",
        capability_service=_CapabilityService(_audit()),
        resolve_context=lambda row: BuildCandidateContextResult(
            candidate=row,
            context=object(),
            unresolved=(),
        ),
        resolve_damage=lambda context: ModeledDamagePotency(
            value=105.0,
            metric_name="single-event expected damage",
        ),
        resolve_sustain=lambda context: _sustain(),
        resolve_assignments=None,
    )

    assert result.damage is not None
    assert result.damage.metric_name == "single-event expected damage"
    assert "DPS" not in result.damage.metric_name
    assert result.comparison.is_rankable


def test_unresolved_damage_metric_blocks_candidate_ranking() -> None:
    result = evaluate_damage_candidate(
        candidate=_candidate("dd:mundus:unknown"),
        baseline_damage=ModeledDamagePotency(
            value=100.0,
            metric_name="single-event expected damage",
        ),
        baseline_capability=_audit(),
        baseline_assignments=None,
        member_id="dd-1",
        capability_service=_CapabilityService(_audit()),
        resolve_context=lambda row: BuildCandidateContextResult(
            candidate=row,
            context=object(),
            unresolved=(),
        ),
        resolve_damage=lambda context: ModeledDamagePotency(
            value=120.0,
            metric_name="single-event expected damage",
            unresolved=("damage type for selected event is unresolved",),
        ),
        resolve_sustain=lambda context: _sustain(),
        resolve_assignments=None,
    )

    assert result.comparison.candidate_value is None
    assert not result.comparison.is_rankable
    assert result.comparison.unresolved == (
        "damage type for selected event is unresolved",
    )
