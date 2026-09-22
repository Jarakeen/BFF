from __future__ import annotations

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_runtime_scenario_frontier_service import (
    ExtremeSustainedDPSRuntimeScenarioFrontierService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
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



def test_candidate_builder_derives_plan_owned_runtime_triggers() -> None:
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=6.0,
            actions=(
                RotationAction(
                    1.0,
                    0,
                    RotationActionKind.ULTIMATE,
                    "Ultimate A",
                    "front",
                ),
            ),
        ),
        refresh_leads=(),
        action_claims=(),
    )
    effect = EffectVariant(
        name="ultimate-proc",
        layer=EffectLayer.PROC,
        source="Ultimate Proc",
        trigger="ultimate_activation_in_combat",
        duration=4.0,
    )

    result = ExtremeSustainedDPSRuntimeScenarioFrontierService().build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        effects=(effect,),
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed boss scenario",
    )

    assert result.unresolved == ()
    assert result.frontier.denominator_proven is True
    assert result.frontier.candidate_count == 1
    attempts = result.frontier.choices[0].snapshot.effect_attempts
    assert any(
        entry.event.trigger == "ultimate_activation_in_combat"
        and entry.event.time_seconds == 1.0
        and entry.event.source == "Ultimate A"
        for entry in attempts
    )


def test_candidate_builder_preserves_open_scenario_trigger_family() -> None:
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )
    effect = EffectVariant(
        name="truth-proc",
        layer=EffectLayer.PROC,
        source="Armor of Truth",
        trigger="damage_off_balance_target",
        duration=10.0,
    )

    result = ExtremeSustainedDPSRuntimeScenarioFrontierService().build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        effects=(effect,),
        supplemental_event_denominator_proven=False,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="partial boss scenario",
    )

    assert result.frontier.denominator_proven is False
    assert any(
        "Scenario-owned runtime event skeleton denominator is not proven complete"
        in row
        for row in result.unresolved
    )



def test_candidate_builder_can_resolve_runtime_effect_universe() -> None:
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=6.0,
            actions=(
                RotationAction(
                    1.0,
                    0,
                    RotationActionKind.ULTIMATE,
                    "Ultimate A",
                    "front",
                ),
            ),
        ),
        refresh_leads=(),
        action_claims=(),
    )
    effect = EffectVariant(
        name="ultimate-proc",
        layer=EffectLayer.PROC,
        source="Ultimate Proc",
        trigger="ultimate_activation_in_combat",
        duration=4.0,
    )

    class _Universe:
        def resolve(self, build):
            return SimpleNamespace(
                effects=(effect,),
                evidence=("candidate runtime effect universe resolved",),
                unresolved=(),
            )

    result = ExtremeSustainedDPSRuntimeScenarioFrontierService(
        runtime_effect_universe=_Universe(),
    ).build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        effects=None,
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed boss scenario",
    )

    assert result.frontier.denominator_proven is True
    assert any(
        "candidate runtime effect universe resolved" in row
        for row in result.evidence
    )


def test_candidate_builder_fails_closed_on_unresolved_runtime_effect_universe() -> None:
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )

    class _Universe:
        def resolve(self, build):
            return SimpleNamespace(
                effects=(),
                evidence=("candidate runtime effect universe unresolved",),
                unresolved=("runtime skill effect identity unresolved",),
            )

    result = ExtremeSustainedDPSRuntimeScenarioFrontierService(
        runtime_effect_universe=_Universe(),
    ).build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        effects=None,
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed boss scenario",
    )

    assert result.frontier.denominator_proven is False
    assert any(
        "runtime skill effect identity unresolved" in row
        for row in result.unresolved
    )
