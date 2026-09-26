from __future__ import annotations

import pytest

from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_runtime_external_history_frontier_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryFrontierService,
)
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
)


def _plan():
    return RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=8.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.SKILL, "A", "front"),
            RotationAction(4.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(5.0, 0, RotationActionKind.SKILL, "B", "back"),
        ),
    )


def _attempt(time_seconds):
    return RuntimeEffectEventAttempt(
        RuntimeEvent(
            time_seconds=float(time_seconds),
            trigger="damage_dealt",
            source="Observed trigger",
        )
    )


def test_proven_external_history_family_becomes_closed_runtime_state_frontier() -> None:
    result = ExtremeSustainedDPSRuntimeExternalHistoryFrontierService().build(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        external_histories=(
            ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                "history:none",
                (),
            ),
            ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                "history:triggered",
                (_attempt(1.0),),
            ),
        ),
        denominator_proven=True,
        source="reviewed encounter runtime family",
    )

    assert result.unresolved == ()
    assert result.frontier.denominator_proven is True
    assert result.frontier.candidate_count == 2
    assert tuple(row.runtime_state_id for row in result.frontier.choices) == (
        "history:none",
        "history:triggered",
    )
    assert all(
        row.snapshot.runtime_history_complete
        for row in result.frontier.choices
    )
    assert all(
        row.snapshot.bar_transition_history_complete
        for row in result.frontier.choices
    )


def test_unproven_external_history_family_keeps_runtime_state_open() -> None:
    result = ExtremeSustainedDPSRuntimeExternalHistoryFrontierService().build(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        external_histories=(
            ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                "history:none",
                (),
            ),
        ),
        denominator_proven=False,
        source="incomplete runtime review",
    )

    assert result.frontier.denominator_proven is False
    assert any(
        "not proven complete" in row
        for row in result.unresolved
    )


def test_invalid_history_choice_fails_entire_runtime_denominator_closed() -> None:
    from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse

    result = ExtremeSustainedDPSRuntimeExternalHistoryFrontierService().build(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        external_histories=(
            ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                "history:bad",
                (ExtremeRuntimePotionUse(2.0),),
            ),
        ),
        denominator_proven=True,
        source="reviewed encounter runtime family",
    )

    assert result.frontier.denominator_proven is False
    assert result.frontier.candidate_count == 0
    assert any(
        "must not supply potion uses" in row
        for row in result.unresolved
    )


def test_runtime_external_history_frontier_rejects_truthy_denominator_proof() -> None:
    with pytest.raises(TypeError, match="denominator_proven must be boolean"):
        ExtremeSustainedDPSRuntimeExternalHistoryFrontierService().build(
            plan=_plan(),
            player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
            external_histories=(
                ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                    "history:none",
                    (),
                ),
            ),
            denominator_proven="true",
            source="invalid proof",
        )


def test_runtime_external_history_frontier_rejects_mutable_history_collection() -> None:
    with pytest.raises(TypeError, match="external histories must be a tuple"):
        ExtremeSustainedDPSRuntimeExternalHistoryFrontierService().build(
            plan=_plan(),
            player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
            external_histories=[],
            denominator_proven=False,
            source="invalid shape",
        )


def test_runtime_external_history_frontier_rejects_mutable_omitted_scope() -> None:
    with pytest.raises(TypeError, match="omitted_scope must be a tuple"):
        ExtremeSustainedDPSRuntimeExternalHistoryFrontierService().build(
            plan=_plan(),
            player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
            external_histories=(
                ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                    "history:none",
                    (),
                ),
            ),
            denominator_proven=True,
            source="invalid shape",
            omitted_scope=["open"],
        )
