from types import SimpleNamespace

import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_multi_demand_role_output_service import (
    RotationCandidateHealerDemandWindowOutput,
    RotationCandidateHealerMultiDemandOutput,
)
from services.rotation_healer_demand_criteria_service import (
    RotationCandidateHealerCriteriaHardObligationService,
    RotationHealerDemandCriterion,
    RotationHealerDemandCriterionSourceKind,
    RotationHealerDemandCriteriaService,
)


def _demand(name: str) -> RotationDemandWindow:
    return RotationDemandWindow(
        name=name,
        start_seconds=10.0,
        end_seconds=15.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.SUSTAINED,
    )


def _window(name: str, value: float | None, unresolved=()):
    demand = _demand(name)
    return RotationCandidateHealerDemandWindowOutput(
        evidence=SimpleNamespace(demand=demand, unresolved=tuple(unresolved)),
        modeled_healing_per_demand_second=value,
    )


def _output(*windows):
    return RotationCandidateHealerMultiDemandOutput(
        candidate_id="healer-candidate",
        windows=tuple(windows),
        unresolved=(),
    )


def _criterion(
    name: str,
    minimum: float,
    source_kind=RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE,
):
    return RotationHealerDemandCriterion(
        demand_name=name,
        minimum_modeled_healing_per_demand_second=minimum,
        source_kind=source_kind,
        provenance=("reviewed encounter evidence",),
    )


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="healer-candidate",
        plan=RotationPlan(
            character_name="Healer",
            build_name="Runtime Healer",
            duration_seconds=30.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _RuntimeMultiDemandOutput:
    def __init__(self) -> None:
        self.calls = []

    def evaluate_windows(self, candidate, *, runtime_build_context_resolver=None):
        self.calls.append((candidate, runtime_build_context_resolver))
        value = 500.0 if runtime_build_context_resolver is None else 1500.0
        return RotationCandidateHealerMultiDemandOutput(
            candidate_id=candidate.candidate_id,
            windows=(_window("burn", value),),
            unresolved=(),
        )


def test_verified_encounter_criteria_can_form_hard_healer_obligations() -> None:
    result = RotationHealerDemandCriteriaService().assess(
        output=_output(_window("first burn", 1200.0), _window("second burn", 800.0)),
        criteria=(
            _criterion("first burn", 1000.0),
            _criterion("second burn", 900.0),
        ),
    )

    assert [item.meets_threshold for item in result.assessments] == [True, False]
    assert result.failed_authoritative == (result.assessments[1],)
    assert result.unresolved_authoritative == ()
    assert not result.hard_obligations_satisfied


def test_caller_assumption_is_diagnostic_not_a_hard_encounter_gate() -> None:
    result = RotationHealerDemandCriteriaService().assess(
        output=_output(_window("burn", 500.0)),
        criteria=(
            _criterion(
                "burn",
                5000.0,
                source_kind=RotationHealerDemandCriterionSourceKind.CALLER_ASSUMPTION,
            ),
        ),
    )

    assessment = result.assessments[0]
    assert assessment.meets_threshold is False
    assert assessment.hard_obligation_satisfied is None
    assert result.failed_authoritative == ()
    assert result.unresolved_authoritative == ()
    assert result.hard_obligations_satisfied


def test_missing_candidate_window_fails_closed_for_verified_criterion() -> None:
    result = RotationHealerDemandCriteriaService().assess(
        output=_output(_window("known burn", 1000.0)),
        criteria=(_criterion("missing burn", 900.0),),
    )

    assessment = result.assessments[0]
    assert assessment.meets_threshold is None
    assert assessment.hard_obligation_satisfied is None
    assert result.unresolved_authoritative == (assessment,)
    assert not result.hard_obligations_satisfied
    assert result.unresolved == (
        "missing burn: candidate healing-window output unavailable",
    )


def test_unresolved_window_stays_unresolved_in_authoritative_criterion() -> None:
    result = RotationHealerDemandCriteriaService().assess(
        output=_output(
            _window(
                "burn",
                None,
                unresolved=("periodic refresh behavior unresolved",),
            )
        ),
        criteria=(_criterion("burn", 900.0),),
    )

    assessment = result.assessments[0]
    assert assessment.meets_threshold is None
    assert not result.hard_obligations_satisfied
    assert assessment.unresolved == (
        "burn: periodic refresh behavior unresolved",
    )


def test_hard_criteria_use_same_runtime_context_as_stabilized_healer_output() -> None:
    output = _RuntimeMultiDemandOutput()
    service = RotationCandidateHealerCriteriaHardObligationService(
        multi_demand_output_service=output,  # type: ignore[arg-type]
        criteria=(_criterion("burn", 1000.0),),
    )
    runtime_resolver = lambda _time, _sequence=None: SimpleNamespace()

    static_result = service.evaluate_plan(_candidate())
    runtime_result = service.evaluate_plan(
        _candidate(),
        runtime_build_context_resolver=runtime_resolver,
    )

    assert static_result.satisfied is False
    assert runtime_result.satisfied is True
    assert output.calls[0][1] is None
    assert output.calls[1][1] is runtime_resolver


def test_criteria_require_provenance_and_unique_demand_names() -> None:
    with pytest.raises(ValueError, match="requires provenance"):
        RotationHealerDemandCriterion(
            demand_name="burn",
            minimum_modeled_healing_per_demand_second=1000.0,
            source_kind=RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE,
            provenance=(),
        )

    service = RotationHealerDemandCriteriaService()
    with pytest.raises(ValueError, match="duplicate healer demand criterion"):
        service.assess(
            output=_output(_window("burn", 1000.0)),
            criteria=(_criterion("burn", 900.0), _criterion("BURN", 800.0)),
        )
