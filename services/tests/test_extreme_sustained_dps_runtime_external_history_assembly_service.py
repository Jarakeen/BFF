from __future__ import annotations

import pytest

from services.extreme_sustained_dps_runtime_attempt_evidence_frontier_service import (
    ExtremeSustainedDPSRuntimeAttemptEvidenceChoice,
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier,
)
from services.extreme_sustained_dps_runtime_external_history_assembly_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryAssemblyResult,
    ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService,
)
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
)


def _attempt_frontier(count=2, *, proven=True):
    choices = tuple(
        ExtremeSustainedDPSRuntimeAttemptEvidenceChoice(
            choice_id=f"attempt:{index}",
            attempts=(),
            evidence=(f"attempt evidence {index}",),
        )
        for index in range(count)
    )
    return ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier(
        choices=choices,
        candidate_count=len(choices),
        denominator_proven=proven,
        evidence=(),
        unresolved=(),
    )


def test_crosses_attempt_and_supplemental_history_families() -> None:
    result = ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService.build(
        attempt_frontier=_attempt_frontier(2),
        supplemental_histories=(
            ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                "supplemental:a",
                ("a",),
            ),
            ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                "supplemental:b",
                ("b",),
            ),
        ),
        supplemental_denominator_proven=True,
        source="reviewed supplemental family",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 4
    assert tuple(row.history_id for row in result.choices) == (
        "attempt:0|supplemental:a",
        "attempt:0|supplemental:b",
        "attempt:1|supplemental:a",
        "attempt:1|supplemental:b",
    )


def test_no_supplemental_entries_becomes_one_explicit_empty_choice() -> None:
    result = ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService.build(
        attempt_frontier=_attempt_frontier(1),
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed no-supplemental scenario",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 1
    assert result.choices[0].entries == ()


def test_unproven_supplemental_denominator_fails_closed() -> None:
    result = ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService.build(
        attempt_frontier=_attempt_frontier(1),
        supplemental_histories=(),
        supplemental_denominator_proven=False,
        source="partial supplemental review",
    )

    assert result.denominator_proven is False
    assert any(
        "Supplemental external runtime-history denominator is not proven complete"
        in row
        for row in result.unresolved
    )


def test_unproven_attempt_denominator_fails_closed() -> None:
    result = ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService.build(
        attempt_frontier=_attempt_frontier(1, proven=False),
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed supplemental family",
    )

    assert result.denominator_proven is False
    assert any(
        "Runtime attempt evidence denominator is not proven complete"
        in row
        for row in result.unresolved
    )


def test_external_history_assembly_rejects_candidate_count_drift() -> None:
    choice = ExtremeSustainedDPSRuntimeExternalHistoryChoice(
        "history",
        (),
    )

    with pytest.raises(ValueError, match="candidate_count must equal choice count"):
        ExtremeSustainedDPSRuntimeExternalHistoryAssemblyResult(
            choices=(choice,),
            candidate_count=2,
            denominator_proven=True,
            evidence=(),
            unresolved=(),
        )


def test_external_history_assembly_requires_strict_denominator_flag() -> None:
    with pytest.raises(TypeError, match="denominator_proven must be boolean"):
        ExtremeSustainedDPSRuntimeExternalHistoryAssemblyResult(
            choices=(),
            candidate_count=0,
            denominator_proven="true",
            evidence=(),
            unresolved=(),
        )
