from minmax.runtime_event import RuntimeEvent
from minmax.support_stacking import StackingBehavior
from minmax.combat_damage_modifiers import damage_taken_from_target_state
from minmax.combat_target_resistance import resistance_reduction_from_target_state
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_sustained_dps_runtime_target_combat_state_service import (
    ExtremeSustainedDPSRuntimeTargetCombatStateService,
)
from services.extreme_sustained_dps_weapon_poison_dilution_selection_service import (
    ExtremeSustainedDPSWeaponPoisonDilutionMode,
    ExtremeSustainedDPSWeaponPoisonDilutionSelection,
    ExtremeSustainedDPSWeaponPoisonSelectedEffect,
)
from services.extreme_sustained_dps_weapon_poison_named_effect_consequence_service import (
    ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService,
)
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonProcOccurrence,
)


def _occurrence(poison_id="Test Poison IX"):
    return ExtremeSustainedDPSWeaponPoisonProcOccurrence(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="weapon_poison_activation",
            source="Light Attack",
            target="Boss",
            source_bar="front",
        ),
        poison_id=poison_id,
    )


def _selection(*effects):
    return ExtremeSustainedDPSWeaponPoisonDilutionSelection(
        poison_id="Test Poison IX",
        formula_id="alchemy_formula:u50:test",
        mode=ExtremeSustainedDPSWeaponPoisonDilutionMode.BASE,
        effects=tuple(effects),
    )


def test_breach_projects_minor_breach_to_enemy_runtime() -> None:
    result = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Breach",
                10.0,
            ),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )

    assert result.resolved is True
    assert len(result.effects) == 1
    effect = result.effects[0]
    assert effect.name == "minor_breach"
    assert effect.duration == 10.0
    assert effect.target == "Boss"
    assert effect.target_type.value == "enemy"
    assert effect.stacking is StackingBehavior.UNIQUE
    assert effect.exclusivity_group == "minor_breach"
    assert effect.chance is None


def test_protection_projects_enemy_vulnerability_and_skips_defensive_self_side() -> None:
    result = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Protection",
                2.5,
            ),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )

    assert result.resolved is True
    assert [effect.name for effect in result.effects] == ["minor_vulnerability"]
    assert any(
        "self-side Minor Protection is irrelevant to sustained outgoing DPS" in row
        for row in result.evidence
    )


def test_unreviewed_damage_trait_remains_fail_closed() -> None:
    result = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Ravage Health",
                6.8,
            ),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )

    assert result.resolved is False
    assert result.effects == ()
    assert any(
        "has no reviewed Objective #32 named-effect relationship" in row
        for row in result.unresolved
    )


def test_consequence_selection_cannot_be_reused_for_different_poison() -> None:
    result = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Breach",
                10.0,
            ),
        )
    ).resolve(
        poison_id="Other Poison IX",
        occurrence=_occurrence("Other Poison IX"),
    )

    assert result.resolved is False
    assert any(
        "consequence selection belongs to Test Poison IX" in row
        for row in result.unresolved
    )


def _project_target_effect(effect):
    attempt = RuntimeEffectEventAttempt.for_bound_effect(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="weapon_poison_proc",
            source="Test Poison IX",
            target="Boss",
            source_bar="front",
        ),
        effect=effect,
        chance_roll=0.0,
    )
    return ExtremeSustainedDPSRuntimeTargetCombatStateService.resolve(
        snapshot=ExtremeRuntimeSnapshot(
            attempts=(attempt,),
            snapshot_time_seconds=2.0,
        ),
        effects=(effect,),
        target_identity="Boss",
    )


def test_poison_minor_breach_reaches_canonical_target_resistance_math() -> None:
    consequence = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect("Breach", 10.0),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )

    projected = _project_target_effect(consequence.effects[0])

    assert projected.unresolved == ()
    assert "Minor Breach" in projected.combat_state.active_buffs
    assert resistance_reduction_from_target_state(projected.combat_state) == 2974.0


def test_poison_minor_vulnerability_reaches_canonical_damage_taken_math() -> None:
    consequence = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect("Protection", 2.5),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )

    projected = _project_target_effect(consequence.effects[0])

    assert projected.unresolved == ()
    assert "Minor Vulnerability" in projected.combat_state.active_buffs
    assert damage_taken_from_target_state(projected.combat_state).generic == 0.05


def test_weapon_power_poison_projects_self_minor_brutality_and_collapses_enemy_maim() -> None:
    result = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Increase Weapon Power",
                5.5,
            ),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )

    assert result.resolved is True
    assert [effect.name for effect in result.effects] == ["minor_brutality"]
    assert result.effects[0].target_type.value == "self"
    assert result.effects[0].target is None
    assert any(
        "enemy-side Minor Maim is irrelevant to sustained outgoing DPS" in row
        for row in result.evidence
    )


def test_poison_self_minor_brutality_reaches_canonical_self_combat_state() -> None:
    consequence = ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
        dilution_selection=_selection(
            ExtremeSustainedDPSWeaponPoisonSelectedEffect(
                "Increase Weapon Power",
                5.5,
            ),
        )
    ).resolve(
        poison_id="Test Poison IX",
        occurrence=_occurrence(),
    )
    effect = consequence.effects[0]
    attempt = RuntimeEffectEventAttempt.for_bound_effect(
        event=RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="weapon_poison_proc",
            source="Test Poison IX",
            source_bar="front",
        ),
        effect=effect,
        chance_roll=0.0,
    )

    from services.extreme_sustained_dps_runtime_self_combat_state_service import (
        ExtremeSustainedDPSRuntimeSelfCombatStateService,
    )

    projected = ExtremeSustainedDPSRuntimeSelfCombatStateService.resolve(
        snapshot=ExtremeRuntimeSnapshot(
            attempts=(attempt,),
            snapshot_time_seconds=2.0,
        ),
        effects=(effect,),
    )

    assert projected.unresolved == ()
    assert projected.combat_state.active_buffs == ("Minor Brutality",)
