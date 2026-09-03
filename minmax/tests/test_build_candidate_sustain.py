from minmax.build_candidate_comparison import ConstraintStatus
from minmax.build_candidate_sustain import compare_sustain_runs
from minmax.build_sustain import BuildSustainRun
from minmax.resource_costs import ResourceType
from minmax.sustain_result import SustainFailure, SustainResult


def _run(
    *,
    sustains: bool,
    minimum: int,
    ending: int,
    unresolved: tuple[str, ...] = (),
) -> BuildSustainRun:
    failure = None
    if not sustains:
        failure = SustainFailure(
            time_seconds=8.0,
            source="Combat Prayer",
            shortfall=120,
            resource_before=400,
            attempted_cost=520,
        )
    sustain = SustainResult(
        resource=ResourceType.MAGICKA,
        sustains=sustains,
        starting_amount=30000,
        ending_amount=ending,
        ending_margin=ending,
        minimum_amount=minimum,
        first_failure=failure,
        total_cost_attempted=10000,
        total_cost_paid=10000 if sustains else 9880,
        total_restoration_applied=4000,
        total_restoration_wasted=0,
    )
    return BuildSustainRun(
        resource=ResourceType.MAGICKA,
        action_cost_events=(),
        recovery_ticks=(),
        restoration_events=(),
        timeline=object(),
        sustain=sustain,
        unresolved=unresolved,
    )


def test_sustain_constraint_preserves_candidate_that_still_sustains() -> None:
    constraint = compare_sustain_runs(
        resource=ResourceType.MAGICKA,
        baseline_run=_run(sustains=True, minimum=6000, ending=8000),
        candidate_run=_run(sustains=True, minimum=5000, ending=7000),
    )
    assert constraint.status is ConstraintStatus.PRESERVED


def test_sustain_constraint_marks_stronger_margin_as_improved() -> None:
    constraint = compare_sustain_runs(
        resource=ResourceType.MAGICKA,
        baseline_run=_run(sustains=True, minimum=6000, ending=8000),
        candidate_run=_run(sustains=True, minimum=7000, ending=9000),
    )
    assert constraint.status is ConstraintStatus.IMPROVED


def test_sustain_constraint_blocks_candidate_resource_failure() -> None:
    constraint = compare_sustain_runs(
        resource=ResourceType.MAGICKA,
        baseline_run=_run(sustains=True, minimum=6000, ending=8000),
        candidate_run=_run(sustains=False, minimum=0, ending=0),
    )
    assert constraint.status is ConstraintStatus.WORSENED
    assert "shortfall 120" in constraint.explanation


def test_sustain_constraint_keeps_unresolved_phase4_evidence_unknown() -> None:
    constraint = compare_sustain_runs(
        resource=ResourceType.MAGICKA,
        baseline_run=_run(sustains=True, minimum=6000, ending=8000),
        candidate_run=_run(
            sustains=True,
            minimum=7000,
            ending=9000,
            unresolved=("candidate action cost unresolved",),
        ),
    )
    assert constraint.status is ConstraintStatus.UNKNOWN


def test_sustain_constraint_repairs_failing_baseline_when_candidate_sustains() -> None:
    constraint = compare_sustain_runs(
        resource=ResourceType.MAGICKA,
        baseline_run=_run(sustains=False, minimum=0, ending=0),
        candidate_run=_run(sustains=True, minimum=2500, ending=4000),
    )
    assert constraint.status is ConstraintStatus.REPAIRED
    assert "repairs failed baseline" in constraint.explanation


def test_sustain_constraint_marks_shared_failure_unsatisfied() -> None:
    constraint = compare_sustain_runs(
        resource=ResourceType.MAGICKA,
        baseline_run=_run(sustains=False, minimum=0, ending=0),
        candidate_run=_run(sustains=False, minimum=0, ending=0),
    )

    assert constraint.status is ConstraintStatus.UNSATISFIED
    assert "Baseline and candidate both fail" in constraint.explanation
    assert "Baseline: first shortfall 120" in constraint.explanation
    assert "candidate: first shortfall 120" in constraint.explanation
