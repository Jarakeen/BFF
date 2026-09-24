from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_runtime_scenario_frontier_service import (
    ExtremeSustainedDPSRuntimeScenarioFrontierService,
)
from services.extreme_sustained_dps_runtime_effect_scaling_service import (
    ExtremeSustainedDPSRuntimeEffectScalingService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
)
from services.extreme_sustained_dps_weapon_enchantment_cooldown_readiness_service import (
    ExtremeSustainedDPSWeaponEnchantmentCooldownState,
)
from services.extreme_sustained_dps_weapon_enchantment_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy,
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
        name="weapon_spell_damage",
        layer=EffectLayer.PROC,
        source="Ultimate Proc",
        magnitude=460.0,
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
    assert result.frontier.choices[0].effects == (effect,)
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


def test_candidate_builder_prunes_proven_non_dps_runtime_effects() -> None:
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )
    effect = EffectVariant(
        name="damage_shield",
        layer=EffectLayer.PROC,
        source="Champion Point: From the Brink",
        trigger="damage_dealt",
        duration=6.0,
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

    assert result.unresolved == ()
    assert result.frontier.denominator_proven is True
    assert any(
        "Runtime effects proven irrelevant to sustained DPS: 1" in row
        for row in result.evidence
    )


def test_candidate_builder_fails_closed_on_unreviewed_runtime_effect_relevance() -> None:
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )
    effect = EffectVariant(
        name="mystery_runtime_power",
        layer=EffectLayer.PROC,
        source="Mystery Proc",
        trigger="damage_dealt",
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

    assert result.frontier.denominator_proven is False
    assert any(
        "no reviewed sustained-DPS relevance disposition" in row
        for row in result.unresolved
    )


def test_candidate_builder_surfaces_typed_relevance_blocker_counts() -> None:
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )
    effect = EffectVariant(
        name="scaled_runtime_debuff",
        layer=EffectLayer.PROC,
        source="Scaled Runtime Debuff",
        trigger="damage_dealt",
        duration=4.0,
        target_type=SupportTargetType.ENEMY,
        resistance_reduction=6000.0,
        scaling="up to 6000 from unresolved source state",
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

    assert result.frontier.denominator_proven is False
    assert any("source-data blockers: 1" in row for row in result.evidence)
    assert any("math/review blockers: 0" in row for row in result.evidence)


def test_candidate_builder_resolves_master_architect_duration_before_runtime_frontier() -> None:
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=30.0,
            actions=(
                RotationAction(
                    1.0,
                    0,
                    RotationActionKind.ULTIMATE,
                    "Aggressive Horn",
                    "front",
                ),
            ),
        ),
        refresh_leads=(),
        action_claims=(),
    )
    effect = EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Master Architect (5)",
        magnitude=10.0,
        duration=1.0,
        scaling="1 second per 10 Ultimate spent",
        trigger="ultimate_activation_in_combat",
        target_type=SupportTargetType.GROUP,
        stacking=StackingBehavior.UNIQUE,
    )

    class _Universe:
        def resolve(self, build):
            return SimpleNamespace(
                effects=(effect,),
                evidence=("candidate runtime effect universe resolved",),
                unresolved=(),
            )

    class _UltimateService:
        def resolve_generation_inputs(self, **_kwargs):
            return SimpleNamespace(
                spend_rule=SimpleNamespace(cost=250.0),
                unresolved=(),
            )

    result = ExtremeSustainedDPSRuntimeScenarioFrontierService(
        runtime_effect_universe=_Universe(),
        runtime_effect_scaling=ExtremeSustainedDPSRuntimeEffectScalingService(
            ultimate_service=_UltimateService(),
        ),
    ).build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(
            Name="Generated",
            BuildName="Candidate",
            Role="DD",
        ),
        effects=None,
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed boss scenario",
    )

    assert result.unresolved == ()
    assert result.frontier.denominator_proven is True
    assert len(result.frontier.choices) == 1
    assert result.frontier.choices[0].effects[0].duration == 25.0
    assert result.frontier.choices[0].effects[0].scaling is None
    assert any(
        "Master Architect duration resolved from canonical Ultimate spend" in row
        for row in result.evidence
    )


def _weapon_enchantment_effect(source, slot):
    return EffectVariant(
        name=source.casefold().replace(" ", "_"),
        layer=EffectLayer.PROC,
        source=source,
        active_bar=BarId.FRONT,
        source_slot=slot,
        trigger="weapon_enchantment_activation",
        duration=5.0,
        stacking=StackingBehavior.UNIQUE,
    )


class _WeaponEnchantmentActivationService:
    def resolve(self, **_kwargs):
        return SimpleNamespace(
            events=(
                RuntimeEvent(
                    time_seconds=1.0,
                    sequence=0,
                    trigger="weapon_enchantment_activation",
                    source="Light Attack",
                    target="Boss",
                    source_bar="front",
                ),
            ),
            evidence=("reviewed weapon-enchantment activation opportunity",),
            unresolved=(),
        )


def test_candidate_builder_binds_one_ready_weapon_enchantment_source() -> None:
    main = _weapon_enchantment_effect("Main Enchant", "main_hand")
    off = _weapon_enchantment_effect("Off Enchant", "off_hand")

    def cooldown_states(**_kwargs):
        return (
            ExtremeSustainedDPSWeaponEnchantmentCooldownState(
                effect=main,
                cooldown_seconds=4.0,
                last_activation_time_seconds=0.0,
            ),
            ExtremeSustainedDPSWeaponEnchantmentCooldownState(
                effect=off,
                cooldown_seconds=4.0,
                last_activation_time_seconds=None,
            ),
        )

    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )
    result = ExtremeSustainedDPSRuntimeScenarioFrontierService(
        weapon_enchantment_activation_service=_WeaponEnchantmentActivationService(),
        weapon_enchantment_cooldown_state_resolver=cooldown_states,
    ).build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        effects=(main, off),
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed weapon enchant scenario",
    )

    assert result.unresolved == ()
    assert result.frontier.denominator_proven is True
    assert result.frontier.candidate_count == 1
    choice = result.frontier.choices[0]
    attempt = choice.snapshot.effect_attempts[0]
    assert choice.effects == ()
    assert attempt.applies_to(off) is True
    assert attempt.applies_to(main) is False
    assert any(
        "Weapon-enchantment source-bound runtime attempts: 1" in row
        for row in result.evidence
    )


def test_candidate_builder_fails_closed_without_weapon_enchantment_cooldown_state() -> None:
    main = _weapon_enchantment_effect("Main Enchant", "main_hand")
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )

    result = ExtremeSustainedDPSRuntimeScenarioFrontierService(
        weapon_enchantment_activation_service=_WeaponEnchantmentActivationService(),
    ).build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        effects=(main,),
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="partial weapon enchant scenario",
    )

    assert result.frontier.denominator_proven is False
    assert any(
        "explicit per-opportunity cooldown-state evidence" in row
        for row in result.unresolved
    )


def test_candidate_builder_can_prove_weapon_enchantment_no_proc() -> None:
    main = _weapon_enchantment_effect("Main Enchant", "main_hand")

    def cooldown_states(**_kwargs):
        return (
            ExtremeSustainedDPSWeaponEnchantmentCooldownState(
                effect=main,
                cooldown_seconds=4.0,
                last_activation_time_seconds=0.0,
            ),
        )

    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )
    result = ExtremeSustainedDPSRuntimeScenarioFrontierService(
        weapon_enchantment_activation_service=_WeaponEnchantmentActivationService(),
        weapon_enchantment_cooldown_state_resolver=cooldown_states,
    ).build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        effects=(main,),
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed weapon enchant scenario",
    )

    assert result.unresolved == ()
    assert result.frontier.denominator_proven is True
    assert result.frontier.choices[0].snapshot.effect_attempts == ()
    assert any(
        "Weapon-enchantment opportunities proven no-proc: 1" in row
        for row in result.evidence
    )


class _TwoWeaponEnchantmentActivationService:
    def resolve(self, **_kwargs):
        return SimpleNamespace(
            events=(
                RuntimeEvent(
                    time_seconds=1.0,
                    sequence=0,
                    trigger="weapon_enchantment_activation",
                    source="Light Attack",
                    target="Boss",
                    source_bar="front",
                ),
                RuntimeEvent(
                    time_seconds=2.0,
                    sequence=1,
                    trigger="weapon_enchantment_activation",
                    source="Light Attack",
                    target="Boss",
                    source_bar="front",
                ),
            ),
            evidence=("two reviewed weapon-enchantment activation opportunities",),
            unresolved=(),
        )


def test_candidate_builder_carries_dual_wield_sequence_branches() -> None:
    main = _weapon_enchantment_effect("Main Enchant", "main_hand")
    off = _weapon_enchantment_effect("Off Enchant", "off_hand")

    def cooldown_policies(**_kwargs):
        return (
            ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy(
                effect=main,
                cooldown_identity="main",
                cooldown_seconds=4.0,
                authoritative=True,
            ),
            ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy(
                effect=off,
                cooldown_identity="off",
                cooldown_seconds=4.0,
                authoritative=True,
            ),
        )

    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )
    result = ExtremeSustainedDPSRuntimeScenarioFrontierService(
        weapon_enchantment_activation_service=_TwoWeaponEnchantmentActivationService(),
        weapon_enchantment_cooldown_policy_resolver=cooldown_policies,
    ).build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD"),
        effects=(main, off),
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed dual wield sequence",
    )

    assert result.unresolved == ()
    assert result.frontier.denominator_proven is True
    assert result.frontier.candidate_count == 2
    assert all(choice.effects == () for choice in result.frontier.choices)
    histories = tuple(
        choice.snapshot.effect_attempts
        for choice in result.frontier.choices
    )
    assert all(len(history) == 2 for history in histories)
    assert all(
        history[0].bound_effect_key != history[1].bound_effect_key
        for history in histories
    )
    assert any(
        "Finite weapon-enchantment source histories: 2" in row
        for row in result.evidence
    )



def test_callable_weapon_enchantment_policy_resolver_receives_player_build() -> None:
    main = _weapon_enchantment_effect("Main Enchant", "main_hand")
    seen = {}

    def cooldown_policies(*, candidate, enchantment_effects, player_build):
        seen["candidate"] = candidate
        seen["effects"] = enchantment_effects
        seen["build"] = player_build
        return (
            ExtremeSustainedDPSWeaponEnchantmentCooldownPolicy(
                effect=main,
                cooldown_identity="main",
                cooldown_seconds=4.0,
                authoritative=True,
            ),
        )

    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )
    build = PlayerBuild(Name="Generated", BuildName="Candidate", Role="DD")

    result = ExtremeSustainedDPSRuntimeScenarioFrontierService(
        weapon_enchantment_activation_service=_WeaponEnchantmentActivationService(),
        weapon_enchantment_cooldown_policy_resolver=cooldown_policies,
    ).build_from_candidate(
        candidate=candidate,
        player_build=build,
        effects=(main,),
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed callable cooldown policy seam",
    )

    assert seen == {
        "candidate": candidate,
        "effects": (main,),
        "build": build,
    }
    assert result.unresolved == ()
    assert result.frontier.denominator_proven is True



class _PoisonActivationService:
    def resolve(self, **_kwargs):
        return SimpleNamespace(
            events=(
                RuntimeEvent(
                    time_seconds=1.0,
                    sequence=0,
                    trigger="weapon_poison_activation",
                    source="Light Attack",
                    target="Boss",
                    source_bar="front",
                ),
            ),
            evidence=("reviewed poison activation opportunity",),
            unresolved=(),
        )


def test_candidate_builder_fails_closed_when_poison_proc_consequences_are_unmodeled() -> None:
    candidate = GeneratedRotationCandidate(
        candidate_id="poison-candidate",
        plan=_plan(),
        refresh_leads=(),
        action_claims=(),
    )

    result = ExtremeSustainedDPSRuntimeScenarioFrontierService(
        weapon_poison_activation_service=_PoisonActivationService(),
    ).build_from_candidate(
        candidate=candidate,
        player_build=PlayerBuild(
            Name="Generated",
            BuildName="Candidate",
            Role="DD",
            FrontBarPoison="Damage Health Poison IX",
        ),
        effects=(),
        occurrence_provider=object(),
        supplemental_event_denominator_proven=True,
        supplemental_histories=(),
        supplemental_denominator_proven=True,
        source="reviewed poison scenario",
    )

    assert result.frontier.denominator_proven is False
    assert any(
        "selected poison effect identity/magnitude/dilution" in row
        for row in result.unresolved
    )
    assert any(
        "Weapon-poison chance/cooldown denominator is proven finite" in row
        for row in result.evidence
    )
