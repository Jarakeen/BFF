from __future__ import annotations

import pytest

from services.extreme_record_result import (
    ExtremeRecordCeilingThreat,
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)


def test_globally_proven_requires_complete_denominator_and_no_open_threats():
    result = ExtremeRecordResult.for_objective(
        "max_health",
        raw_value=81234,
        proof_status=ExtremeRecordProofStatus.PROVEN,
        winning_build={"race": "Nord"},
        search_coverage=ExtremeRecordSearchCoverage(
            searched=("all legal races", "all legal gear"),
            candidates_screened=1200,
            candidates_optimized=1200,
            denominator_proven=True,
        ),
    )

    assert result.globally_proven
    assert result.objective_key == "max_health"


def test_proven_label_does_not_override_incomplete_search_denominator():
    result = ExtremeRecordResult.for_objective(
        "weapon_damage",
        raw_value=9999,
        proof_status="proven",
        search_coverage=ExtremeRecordSearchCoverage(
            searched=("saved-build mutations",),
            omitted=("class change",),
            denominator_proven=False,
        ),
    )

    assert not result.globally_proven


def test_conditional_record_preserves_runtime_prerequisites_separately():
    result = ExtremeRecordResult.for_objective(
        "actual_heal",
        raw_value=21854.398,
        proof_status="conditional",
        runtime_prerequisites=("pet summoned and alive", "potion window active"),
        self_provided_conditions=("pet activation",),
        external_conditions=(),
    )

    assert result.conditionally_achievable
    assert result.runtime_prerequisites == (
        "pet summoned and alive",
        "potion window active",
    )
    assert not result.globally_proven


def test_unresolved_ceiling_threat_blocks_global_proof():
    threat = ExtremeRecordCeilingThreat(
        source="Blood of the Elder Dragon",
        lower_bound=17870.761,
        upper_bound=26806.142,
        reason="missing-Health interpolation unresolved",
    )
    result = ExtremeRecordResult.for_objective(
        "actual_heal",
        raw_value=21854.398,
        proof_status="proven",
        ceiling_threats=(threat,),
        search_coverage=ExtremeRecordSearchCoverage(denominator_proven=True),
    )

    assert threat.bounded
    assert not result.globally_proven


def test_raw_and_effective_values_are_kept_distinct_for_capped_records():
    result = ExtremeRecordResult.for_objective(
        "physical_resistance",
        raw_value=55000,
        effective_value=33000,
        effective_cap=33000,
        proof_status="conditional",
        runtime_prerequisites=("defensive proc active",),
    )

    assert result.raw_value == 55000
    assert result.effective_value == 33000
    assert result.effective_cap == 33000
    assert result.has_effective_cap_interpretation


def test_lower_bound_record_is_not_mistaken_for_proven_or_conditional():
    result = ExtremeRecordResult.for_objective(
        "invisibility_uptime",
        raw_value=0.75,
        proof_status="lower_bound",
        unresolved=("complete repeatable sustain cycle not yet modeled",),
    )

    assert not result.globally_proven
    assert not result.conditionally_achievable


def test_unknown_proof_status_fails_closed():
    with pytest.raises(ValueError, match="Unsupported Extreme Record proof status"):
        ExtremeRecordResult.for_objective(
            "max_health",
            raw_value=1,
            proof_status="probably",
        )


def test_unknown_objective_fails_closed():
    with pytest.raises(ValueError, match="Unsupported Extreme Records objective"):
        ExtremeRecordResult.for_objective(
            "maximum_vibes",
            raw_value=100,
            proof_status="proven",
        )
