from __future__ import annotations

import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.extreme_sustained_dps_encounter_policy_frontier_service import (
    ExtremeSustainedDPSEncounterPolicyChoice,
    ExtremeSustainedDPSEncounterPolicyFrontierService,
)
from services.extreme_sustained_dps_generated_encounter_policy_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedEncounterPolicyAxisAdapterService,
)


def _demand(name="Burst"):
    return RotationDemandWindow(
        name=name,
        start_seconds=5.0,
        end_seconds=8.0,
        kind=RotationDemandKind.DAMAGE,
        pattern=RotationDemandPattern.BURST,
        target_count=1,
    )


def test_generated_encounter_policy_axis_preserves_explicit_demands_and_coverage() -> None:
    frontier = ExtremeSustainedDPSEncounterPolicyFrontierService.build(
        (
            ExtremeSustainedDPSEncounterPolicyChoice(
                "policy:a",
                (_demand(),),
            ),
        ),
        denominator_proven=True,
        source="reviewed encounter policy",
    )
    adapter = ExtremeSustainedDPSGeneratedEncounterPolicyAxisAdapterService(
        frontier=frontier
    )
    state = adapter.root("assembled")

    axis = adapter.axes()[0]
    assert axis.canonical_axes == ("encounter_policy",)
    assert axis.candidate_count(state) == 1

    selected = axis.candidate_at(state, 0)
    assert selected.complete is True
    assert selected.choice.policy_id == "policy:a"
    assert selected.choice.demands[0].name == "Burst"
    assert adapter.coverage().dominated_axes == ("encounter_policy",)


def test_unproven_encounter_policy_denominator_fails_closed() -> None:
    frontier = ExtremeSustainedDPSEncounterPolicyFrontierService.build(
        (
            ExtremeSustainedDPSEncounterPolicyChoice(
                "policy:a",
                (_demand(),),
            ),
        ),
        denominator_proven=False,
        source="open review",
    )
    adapter = ExtremeSustainedDPSGeneratedEncounterPolicyAxisAdapterService(
        frontier=frontier
    )

    try:
        adapter.axes()[0].candidate_count(adapter.root("assembled"))
    except ValueError as exc:
        assert "proven finite denominator" in str(exc)
    else:
        raise AssertionError("unproven encounter-policy denominator should fail closed")


def test_generated_encounter_policy_axis_rejects_boolean_index() -> None:
    frontier = ExtremeSustainedDPSEncounterPolicyFrontierService.build(
        (
            ExtremeSustainedDPSEncounterPolicyChoice(
                "policy:a",
                (_demand(),),
            ),
        ),
        denominator_proven=True,
        source="reviewed encounter policy",
    )
    adapter = ExtremeSustainedDPSGeneratedEncounterPolicyAxisAdapterService(
        frontier=frontier
    )

    with pytest.raises(TypeError, match="choice index must be an integer"):
        adapter.axes()[0].candidate_at(adapter.root("assembled"), True)
