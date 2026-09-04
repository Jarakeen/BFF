import pytest

from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_candidate_source import (
    PrescribedObjectiveMeasurement,
    PrescribedOpenSlotCandidate,
    evaluate_open_slot_candidate_source,
)
from services.team_prescription_pipeline import (
    run_automatic_team_prescription_candidate_pipeline,
)


def _roster() -> PrescribedRoster:
    return PrescribedRoster(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        scope=TeamPrescriptionScope(
            dimensions=(PrescriptionDimension.CLASS, PrescriptionDimension.BUILD)
        ),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Main Tank",
                player_name="Susan",
                source_build_name="Necro Tank",
                prescribed_role="Tank",
            ),
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 1: requires evidence",),
            ),
        ),
        unresolved=("DD 1: requires evidence",),
    )


def _candidate(candidate_id: str, *, role: str = "DD") -> PrescribedOpenSlotCandidate:
    return PrescribedOpenSlotCandidate.from_build(
        candidate_id=candidate_id,
        candidate_build=PlayerBuild(
            Name=candidate_id,
            BuildName=f"{candidate_id} Build",
            Role=role,
            EsoClass="Arcanist" if role == "DD" else "Necromancer",
        ),
        candidate_source="phase13:test-open-slot",
    )


def _measurement(
    value: float,
    *,
    status: ConstraintStatus = ConstraintStatus.PRESERVED,
) -> PrescribedObjectiveMeasurement:
    return PrescribedObjectiveMeasurement(
        objective=EvaluationObjective.DAMAGE,
        value=value,
        metric_name="canonical single-event expected damage",
        constraints=(
            CandidateConstraint(
                name="magicka sustain",
                status=status,
                explanation="authoritative sustain evidence",
            ),
        ),
        evidence=("canonical DD evaluator",),
    )


def test_source_evaluates_only_role_compatible_open_slot_candidates() -> None:
    evaluated: list[tuple[str, str]] = []

    def evaluate(candidate, slot_name):
        evaluated.append((candidate.candidate_id, slot_name))
        return _measurement(125.0)

    result = evaluate_open_slot_candidate_source(
        roster=_roster(),
        candidates=(_candidate("dd"), _candidate("tank", role="Tank")),
        evaluate_objective=evaluate,
    )

    assert evaluated == [("dd", "DD 1")]
    assert tuple(result.evidence_by_slot) == ("DD 1",)
    assert result.evidence_by_slot["DD 1"][0].candidate.candidate_id == "dd"
    assert result.unresolved == ()


def test_automatic_pipeline_uses_absolute_evidence_without_fake_baseline() -> None:
    values = {"lower": 115.0, "winner": 130.0}

    result = run_automatic_team_prescription_candidate_pipeline(
        roster=_roster(),
        candidates=(_candidate("lower"), _candidate("winner")),
        evaluate_objective=lambda candidate, _slot: _measurement(
            values[candidate.candidate_id]
        ),
    )

    prescribed = result.final_roster.assignments[1]
    assert prescribed.source_build_name == "winner Build"
    assert result.optimization.applied_count == 1
    winner = result.optimization.slots[1].ranking.recommended
    assert winner.comparison is None
    assert winner.open_slot.measurement.value == 130.0
    reason = prescribed.change_for(PrescriptionDimension.BUILD).reason
    assert "absolute canonical single-event expected damage 130.000" in reason
    assert "baseline" not in reason.casefold()


def test_automatic_pipeline_blocks_higher_objective_with_failed_hard_constraint() -> None:
    def evaluate(candidate, _slot):
        if candidate.candidate_id == "unsafe":
            return _measurement(160.0, status=ConstraintStatus.UNSATISFIED)
        return _measurement(125.0)

    result = run_automatic_team_prescription_candidate_pipeline(
        roster=_roster(),
        candidates=(_candidate("unsafe"), _candidate("safe")),
        evaluate_objective=evaluate,
    )

    assert result.final_roster.assignments[1].source_build_name == "safe Build"
    rejection = result.optimization.slots[1].ranking.rejected[0]
    assert rejection.candidate_id == "unsafe"
    assert "absolute objective is not rankable" in rejection.reasons


def test_automatic_pipeline_enforces_provider_evidence_before_objective() -> None:
    result = run_automatic_team_prescription_candidate_pipeline(
        roster=_roster(),
        candidates=(_candidate("raw"), _candidate("provider")),
        evaluate_objective=lambda candidate, _slot: _measurement(
            150.0 if candidate.candidate_id == "raw" else 125.0
        ),
        resolve_provider_requirements=lambda candidate, _slot: (
            ("sunspire:provider",) if candidate.candidate_id == "provider" else ()
        ),
        provider_requirements_by_slot={"DD 1": ("sunspire:provider",)},
    )

    assert result.final_roster.assignments[1].source_build_name == "provider Build"


def test_source_keeps_evaluation_failure_explicit() -> None:
    result = evaluate_open_slot_candidate_source(
        roster=_roster(),
        candidates=(_candidate("unknown"),),
        evaluate_objective=lambda _candidate, _slot: (_ for _ in ()).throw(
            ValueError("canonical context unavailable")
        ),
    )

    assert result.evidence_by_slot["DD 1"] == ()
    assert any("canonical context unavailable" in item for item in result.unresolved)
    assert any("no role-compatible build template produced" in item for item in result.unresolved)


def test_source_rejects_duplicate_candidate_ids() -> None:
    with pytest.raises(ValueError, match="duplicate candidate_id"):
        evaluate_open_slot_candidate_source(
            roster=_roster(),
            candidates=(_candidate("same"), _candidate("same")),
            evaluate_objective=lambda _candidate, _slot: _measurement(100.0),
        )
