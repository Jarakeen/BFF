from __future__ import annotations

from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.extreme_runtime_bar_transition import ExtremeRuntimeBarTransition
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeWitnessCompositionService,
)


def _plan():
    return RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=10.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.SKILL, "A", "front"),
            RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(6.0, 0, RotationActionKind.SKILL, "B", "back"),
        ),
    )


def _attempt(time_seconds, sequence=0):
    return RuntimeEffectEventAttempt(
        RuntimeEvent(
            time_seconds=float(time_seconds),
            sequence=int(sequence),
            trigger="damage_dealt",
            source="Observed trigger",
        )
    )


def test_composer_tags_external_attempts_and_projects_plan_bar_transitions() -> None:
    result = ExtremeSustainedDPSRuntimeWitnessCompositionService().compose(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        external_entries=(_attempt(1.0), _attempt(6.0)),
    )

    assert result.resolved is True
    assert result.snapshot is not None
    assert result.snapshot.bar_transition_history_complete is True
    assert tuple(
        (row.time_seconds, row.from_bar, row.to_bar)
        for row in result.snapshot.bar_transitions
    ) == ((5.0, "front", "back"),)
    assert tuple(row.active_bar for row in result.snapshot.bar_effect_attempts) == (
        "front",
        "back",
    )


def test_external_bar_transition_is_rejected_as_competing_truth() -> None:
    result = ExtremeSustainedDPSRuntimeWitnessCompositionService().compose(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        external_entries=(
            ExtremeRuntimeBarTransition(5.0, 0, "front", "back"),
        ),
    )

    assert result.resolved is False
    assert any("must not supply bar transitions" in row for row in result.unresolved)


def test_external_potion_use_is_rejected_as_competing_truth() -> None:
    result = ExtremeSustainedDPSRuntimeWitnessCompositionService().compose(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        external_entries=(ExtremeRuntimePotionUse(2.0),),
    )

    assert result.resolved is False
    assert any("must not supply potion uses" in row for row in result.unresolved)



def test_empty_external_history_is_authoritative_when_plan_has_no_runtime_events() -> None:
    plan = RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=5.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.SKILL, "A", "front"),
        ),
    )
    result = ExtremeSustainedDPSRuntimeWitnessCompositionService().compose(
        plan=plan,
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        external_entries=(),
    )

    assert result.resolved is True
    assert result.snapshot is not None
    assert result.snapshot.runtime_history == ()
    assert result.snapshot.runtime_history_complete is True
    assert result.snapshot.bar_transition_history_complete is True
