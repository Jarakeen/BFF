from __future__ import annotations

import pytest

from types import SimpleNamespace

from services.extreme_sustained_dps_finite_whole_plan_dominance_service import (
    ExtremeSustainedDPSWholePlanEvaluation,
)
from services.extreme_sustained_dps_runtime_state_dominance_search_service import (
    ExtremeSustainedDPSRuntimeStateDominanceSearchService,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
    ExtremeSustainedDPSRuntimeStateFrontierService,
)


class _Evaluator:
    def __init__(self, rows):
        self.rows = rows

    def evaluate(self, choice):
        return self.rows[choice.runtime_state_id]


def _frontier():
    return ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (
            ExtremeSustainedDPSRuntimeStateChoice("base", object()),
            ExtremeSustainedDPSRuntimeStateChoice("buffed", object()),
        ),
        denominator_proven=True,
        source="closed runtime family",
        omitted_scope=("encounter-driven runtime states remain open",),
    )


def _row(identity, dps):
    return ExtremeSustainedDPSWholePlanEvaluation(
        choice_id=identity,
        modeled_dps=dps,
        duration_seconds=20.0,
        mechanic_complete=True,
    )


def test_complete_runtime_family_promotes_runtime_state_axis_and_ceiling() -> None:
    service = ExtremeSustainedDPSRuntimeStateDominanceSearchService(
        ".",
        scenario=SimpleNamespace(plan=SimpleNamespace(duration_seconds=20.0)),
        evaluator=_Evaluator(
            {
                "base": _row("base", 100.0),
                "buffed": _row("buffed", 140.0),
            }
        ),
    )

    result = service.search(
        candidate_key="branch:runtime",
        frontier=_frontier(),
    )

    assert result.axis_coverage.dominated_axes == ("runtime_state",)
    assert result.bound.proven_safe is True
    assert result.upper_bound_dps == 140.0
    assert result.winning_choice_id == "buffed"
    assert result.omitted_scope == ("encounter-driven runtime states remain open",)


def test_open_runtime_family_cannot_promote_numeric_ceiling() -> None:
    frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (ExtremeSustainedDPSRuntimeStateChoice("base", object()),),
        denominator_proven=False,
        source="partial runtime family",
    )
    service = ExtremeSustainedDPSRuntimeStateDominanceSearchService(
        ".",
        scenario=SimpleNamespace(plan=SimpleNamespace(duration_seconds=20.0)),
        evaluator=_Evaluator({"base": _row("base", 100.0)}),
    )

    result = service.search(candidate_key="branch:runtime-open", frontier=frontier)

    assert result.axis_coverage.dominated_axes == ()
    assert result.bound.proven_safe is False


def test_runtime_state_adapter_rejects_boolean_index() -> None:
    service = ExtremeSustainedDPSRuntimeStateDominanceSearchService(
        ".",
        scenario=SimpleNamespace(plan=SimpleNamespace(duration_seconds=20.0)),
        evaluator=_Evaluator(
            {
                "base": _row("base", 100.0),
                "buffed": _row("buffed", 140.0),
            }
        ),
    )

    from services.extreme_sustained_dps_runtime_state_dominance_search_service import (
        _RuntimeStateWholePlanAdapter,
    )

    adapter = _RuntimeStateWholePlanAdapter(_frontier())
    with pytest.raises(TypeError, match="choice index must be an integer"):
        adapter.choice_at(True)


def test_runtime_state_adapter_preserves_strict_frontier_proof_types() -> None:
    from dataclasses import replace
    from services.extreme_sustained_dps_runtime_state_dominance_search_service import (
        _RuntimeStateWholePlanAdapter,
    )

    frontier = _frontier()
    bad = replace(frontier, denominator_proven="true")  # type: ignore[arg-type]
    adapter = _RuntimeStateWholePlanAdapter(bad)

    with pytest.raises(TypeError, match="denominator_proven must be boolean"):
        _ = adapter.denominator_proven
