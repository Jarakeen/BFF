from __future__ import annotations

import pytest

from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
    ExtremeSustainedDPSRuntimeStateFrontier,
    ExtremeSustainedDPSRuntimeStateFrontierService,
)


def _choice(identity: str, *, unresolved=()):
    return ExtremeSustainedDPSRuntimeStateChoice(
        runtime_state_id=identity,
        snapshot=object(),
        unresolved=tuple(unresolved),
    )


def test_complete_external_runtime_family_promotes_local_denominator() -> None:
    frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (_choice("base"), _choice("proc")),
        denominator_proven=True,
        source="reviewed finite runtime family",
        omitted_scope=("encounter-triggered states remain open",),
    )

    assert frontier.denominator_proven is True
    assert frontier.candidate_count == 2
    assert frontier.unresolved == ()
    assert frontier.omitted_scope == ("encounter-triggered states remain open",)


def test_unproven_runtime_family_stays_open() -> None:
    frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (_choice("base"),),
        denominator_proven=False,
        source="partial runtime family",
    )

    assert frontier.denominator_proven is False
    assert any("not externally proven complete" in row for row in frontier.unresolved)


def test_duplicate_runtime_identity_blocks_closure() -> None:
    frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (_choice("same"), _choice("same")),
        denominator_proven=True,
        source="bad runtime family",
    )

    assert frontier.denominator_proven is False
    assert frontier.candidate_count == 1
    assert any("Duplicate runtime-state identity" in row for row in frontier.unresolved)


def test_choice_unresolved_blocks_runtime_family_closure() -> None:
    frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (_choice("gap", unresolved=("proc timing unresolved",)),),
        denominator_proven=True,
        source="runtime family",
    )

    assert frontier.denominator_proven is False
    assert any("proc timing unresolved" in row for row in frontier.unresolved)


def test_runtime_state_choice_normalizes_diagnostics() -> None:
    choice = ExtremeSustainedDPSRuntimeStateChoice(
        runtime_state_id="  runtime:test ",
        snapshot=object(),
        evidence=(" source ", "source", ""),
        unresolved=(" gap ", "gap", ""),
    )

    assert choice.runtime_state_id == "runtime:test"
    assert choice.evidence == ("source",)
    assert choice.unresolved == ("gap",)


def test_runtime_state_frontier_rejects_candidate_count_drift() -> None:
    choice = _choice("base")

    with pytest.raises(
        ValueError,
        match="candidate_count must equal retained choice count",
    ):
        ExtremeSustainedDPSRuntimeStateFrontier(
            choices=(choice,),
            candidate_count=2,
            denominator_proven=True,
            evidence=(),
            unresolved=(),
            omitted_scope=(),
        )


def test_runtime_state_frontier_rejects_proven_state_with_unresolved_evidence() -> None:
    choice = _choice("base")

    with pytest.raises(
        ValueError,
        match="denominator cannot be proven",
    ):
        ExtremeSustainedDPSRuntimeStateFrontier(
            choices=(choice,),
            candidate_count=1,
            denominator_proven=True,
            evidence=(),
            unresolved=("gap",),
            omitted_scope=(),
        )


def test_runtime_state_choice_rejects_mutable_proof_collections() -> None:
    with pytest.raises(TypeError, match="evidence must be a tuple"):
        ExtremeSustainedDPSRuntimeStateChoice(
            runtime_state_id="runtime:test",
            snapshot=object(),
            evidence=["mutable"],
        )


def test_runtime_state_frontier_builder_rejects_truthy_non_boolean_proof() -> None:
    with pytest.raises(TypeError, match="proof flag must be boolean"):
        ExtremeSustainedDPSRuntimeStateFrontierService.build(
            (_choice("base"),),
            denominator_proven="false",
            source="invalid proof",
        )


def test_runtime_state_frontier_builder_requires_tuple_choices() -> None:
    with pytest.raises(TypeError, match="choices must be a tuple"):
        ExtremeSustainedDPSRuntimeStateFrontierService.build(
            [_choice("base")],
            denominator_proven=True,
            source="invalid collection",
        )
