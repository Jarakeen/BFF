from __future__ import annotations

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_runtime_scenario_frontier_service import (
    ExtremeSustainedDPSRuntimeScenarioFrontierService,
)
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
)


def _plan():
    return RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=6.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.SKILL, "A", "front"),
        ),
    )


def _event():
    return RuntimeEvent(
        time_seconds=1.0,
        trigger="damage_dealt",
        source="Attack",
        target="Boss",
    )


def _effect():
    return EffectVariant(
        name="proc",
        layer=EffectLayer.PROC,
        source="Proc",
        trigger="damage_dealt",
        chance=0.5,
        duration=4.0,
    )


def test_scenario_builder_produces_closed_runtime_state_frontier() -> None:
    result = ExtremeSustainedDPSRuntimeScenarioFrontierService().build(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        events=(_event(),),
        effects=(_effect(),),
        event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed boss scenario",
    )

    assert result.unresolved == ()
    assert result.frontier.denominator_proven is True
    assert result.frontier.candidate_count == 2
    assert result.frontier.omitted_scope == ()
    assert any("closure-ready" in row for row in result.evidence)


def test_scenario_builder_preserves_supplemental_history_cross_product() -> None:
    result = ExtremeSustainedDPSRuntimeScenarioFrontierService().build(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        events=(_event(),),
        effects=(_effect(),),
        event_denominator_proven=True,
        supplemental_histories=(
            ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                "supplemental:a",
                (),
            ),
            ExtremeSustainedDPSRuntimeExternalHistoryChoice(
                "supplemental:b",
                (),
            ),
        ),
        supplemental_denominator_proven=True,
        source="reviewed boss scenario",
    )

    assert result.frontier.denominator_proven is True
    assert result.frontier.candidate_count == 4


def test_scenario_builder_fails_closed_when_event_family_is_unproven() -> None:
    result = ExtremeSustainedDPSRuntimeScenarioFrontierService().build(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        events=(_event(),),
        effects=(_effect(),),
        event_denominator_proven=False,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="partial boss scenario",
    )

    assert result.frontier.denominator_proven is False
    assert any(
        "event skeleton denominator is not proven complete" in row
        for row in result.unresolved
    )


def test_scenario_builder_preserves_explicit_omitted_scope() -> None:
    result = ExtremeSustainedDPSRuntimeScenarioFrontierService().build(
        plan=_plan(),
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        events=(),
        effects=(),
        event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed boss scenario",
        omitted_scope=("external debuff timing family omitted",),
    )

    assert result.frontier.denominator_proven is True
    assert result.frontier.omitted_scope == (
        "external debuff timing family omitted",
    )
    assert any("remains open" in row for row in result.evidence)
