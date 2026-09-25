from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_event import RuntimeEvent
from minmax.combat_target_resistance import resistance_reduction_from_target_state
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_weapon_poison_consequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService,
)
from services.extreme_sustained_dps_weapon_poison_dilution_selection_service import (
    ExtremeSustainedDPSWeaponPoisonDilutionMode,
    ExtremeSustainedDPSWeaponPoisonDilutionSelection,
    ExtremeSustainedDPSWeaponPoisonSelectedEffect,
)
from services.extreme_sustained_dps_weapon_poison_named_effect_consequence_service import (
    ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_sustained_dps_runtime_target_combat_state_service import (
    ExtremeSustainedDPSRuntimeTargetCombatStateService,
)
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonSequenceFrontierService,
)


def _event(time_seconds=1.0, sequence=0):
    return RuntimeEvent(
        time_seconds=time_seconds,
        sequence=sequence,
        trigger="weapon_poison_activation",
        source="Weapon Hit",
        target="Boss",
        source_bar="front",
    )


def _sequence(events=(_event(),)):
    return ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
        events=events,
        player_build=PlayerBuild(FrontBarPoison="Damage Health Poison IX"),
        event_denominator_proven=True,
        source="reviewed poison cadence",
    )


def _effect(*, chance=None):
    return EffectVariant(
        name="poison_damage_runtime",
        layer=EffectLayer.PROC,
        source="Damage Health Poison IX",
        magnitude=100.0,
        duration=1.0,
        chance=chance,
        trigger="weapon_poison_proc",
    )


class _Resolver:
    def __init__(self, effects=(_effect(),), unresolved=()):
        self.effects = tuple(effects)
        self.unresolved = tuple(unresolved)

    def resolve(self, *, poison_id, occurrence):
        return SimpleNamespace(
            effects=self.effects,
            evidence=(f"resolved {poison_id}",),
            unresolved=self.unresolved,
        )


def test_selected_poison_proc_branches_become_bound_runtime_attempts() -> None:
    result = ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService(
        consequence_resolver=_Resolver()
    ).build(
        sequence_frontier=_sequence(),
        source="reviewed poison consequences",
    )

    assert result.resolved is True
    assert result.attempt_frontier is not None
    assert result.attempt_frontier.denominator_proven is True
    assert result.attempt_frontier.candidate_count == 2
    assert result.effects == (_effect(),)

    attempt_counts = sorted(
        len(choice.attempts)
        for choice in result.attempt_frontier.choices
    )
    assert attempt_counts == [0, 1]

    proc_choice = next(
        choice
        for choice in result.attempt_frontier.choices
        if choice.attempts
    )
    attempt = proc_choice.attempts[0]
    assert attempt.event.trigger == "weapon_poison_proc"
    assert attempt.event.source == "Damage Health Poison IX"
    assert attempt.event.target == "Boss"
    assert attempt.event.source_bar == "front"
    assert attempt.bound_effect_key is not None


def test_poison_consequence_resolver_must_return_explicit_runtime_effects() -> None:
    result = ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService(
        consequence_resolver=_Resolver(effects=())
    ).build(
        sequence_frontier=_sequence(),
        source="empty poison consequences",
    )

    assert result.resolved is False
    assert result.attempt_frontier is not None
    assert result.attempt_frontier.denominator_proven is False
    assert any(
        "returned no explicit runtime effects" in row
        for row in result.unresolved
    )


def test_poison_consequence_does_not_roll_proc_chance_twice() -> None:
    result = ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService(
        consequence_resolver=_Resolver(effects=(_effect(chance=0.2),))
    ).build(
        sequence_frontier=_sequence(),
        source="double chance poison consequence",
    )

    assert result.resolved is False
    assert any(
        "carries an extra proc chance" in row
        for row in result.unresolved
    )


def test_repeated_selected_poison_procs_share_one_runtime_effect_definition() -> None:
    result = ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService(
        consequence_resolver=_Resolver()
    ).build(
        sequence_frontier=_sequence((_event(1.0, 0), _event(11.0, 1))),
        source="repeated poison consequences",
    )

    assert result.effects == (_effect(),)
    assert any(
        len(choice.attempts) == 2
        for choice in result.attempt_frontier.choices
    )


def test_named_poison_consequence_frontier_reaches_target_combat_math() -> None:
    resolver = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=ExtremeSustainedDPSWeaponPoisonDilutionSelection(
            poison_id="Damage Health Poison IX",
            formula_id="alchemy_formula:u50:test",
            mode=ExtremeSustainedDPSWeaponPoisonDilutionMode.BASE,
            effects=(
                ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                    effect_name="Breach",
                    duration_seconds=10.0,
                ),
            ),
        )
    )
    consequence = ExtremeSustainedDPSWeaponPoisonConsequenceFrontierService(
        consequence_resolver=resolver
    ).build(
        sequence_frontier=_sequence(),
        source="reviewed exact poison consequence",
    )

    assert consequence.resolved is True
    assert consequence.attempt_frontier is not None
    assert consequence.attempt_frontier.denominator_proven is True
    assert [effect.name for effect in consequence.effects] == ["minor_breach"]

    proc_choice = next(
        choice
        for choice in consequence.attempt_frontier.choices
        if choice.attempts
    )
    projected = ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=ExtremeRuntimeSnapshot(
            attempts=proc_choice.attempts,
            snapshot_time_seconds=2.0,
        ),
        effects=consequence.effects,
        target_identity="Boss",
    )

    assert projected.unresolved == ()
    assert "Minor Breach" in projected.combat_state.active_buffs
    assert resistance_reduction_from_target_state(projected.combat_state) == 2974.0
