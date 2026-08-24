from minmax.character_build.bar import Bar
from minmax.character_build.capability_resolver import CharacterCapabilityResolver
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.effect_relationship import (
    EffectRelationship,
    EffectRelationshipType,
    apply_relationships,
    resolve_condition_eligibility,
)
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role
from minmax.roster_capability_resolver import RosterCapabilityResolver
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType

# These tests exercise the generic condition/proc/relationship engine
# mechanics only, using deliberately fictional source/effect names (see
# test_effect_relationship.py for the same convention). Real-data
# coverage lives in test_character_build_real_data_integration.py.


def _bar() -> Bar:
    slots = tuple(
        SlottedSkill(
            skill_id=f"test_skill_{i}",
            skill_line_id="animal_companions",
            is_ultimate=(i == 5),
        )
        for i in range(6)
    )
    return Bar(
        bar_id=BarId.FRONT,
        main_hand=Weapon(WeaponType.RESTORATION_STAFF),
        off_hand=None,
        slots=slots,
    )


def _build_with_effect(effect: EffectVariant) -> CharacterBuild:
    armor = ArmorPiece(slot=GearSlot.HEAD, effects=(effect,))
    return CharacterBuild(
        name="Condition Test",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=(armor,),
        front_bar=_bar(),
    )


# ---------------------------------------------------------------------
# 1-4. Condition resolution
# ---------------------------------------------------------------------


def test_effect_with_no_condition_is_eligible():
    effect = EffectVariant(
        name="fictional_unconditional_buff",
        layer=EffectLayer.CAST,
        source="Fictional Skill",
    )

    (resolved,) = resolve_condition_eligibility([effect], frozenset())

    assert resolved.eligible is True


def test_effect_with_unsatisfied_condition_is_not_eligible():
    effect = EffectVariant(
        name="fictional_conditional_buff",
        layer=EffectLayer.CAST,
        source="Fictional Skill",
        condition="fictional_condition_a",
    )

    (resolved,) = resolve_condition_eligibility([effect], frozenset())

    assert resolved.eligible is False
    # Evidence is preserved, not discarded, when a condition is unmet.
    assert resolved.name == "fictional_conditional_buff"
    assert resolved.condition == "fictional_condition_a"


def test_effect_with_satisfied_condition_is_eligible():
    effect = EffectVariant(
        name="fictional_conditional_buff",
        layer=EffectLayer.CAST,
        source="Fictional Skill",
        condition="fictional_condition_a",
    )

    (resolved,) = resolve_condition_eligibility(
        [effect], frozenset({"fictional_condition_a"})
    )

    assert resolved.eligible is True


def test_condition_is_preserved_as_evidence_when_context_absent():
    """
    With no context supplied at all, conditions are not evaluated (an
    effect stays eligible) - but the condition itself is still carried
    on the resolved instance rather than being dropped.
    """
    effect = EffectVariant(
        name="fictional_conditional_buff",
        layer=EffectLayer.CAST,
        source="Fictional Skill",
        condition="fictional_condition_a",
    )

    result = apply_relationships([effect], [])

    assert result[0].eligible is True
    assert result[0].condition == "fictional_condition_a"


# ---------------------------------------------------------------------
# 5. Multiple required conditions (via multiple REQUIRES relationships)
# ---------------------------------------------------------------------


def test_multiple_required_conditions_all_satisfied():
    base = EffectVariant(
        name="fictional_gated_effect",
        layer=EffectLayer.CAST,
        source="Fictional Skill",
    )
    requires_a = EffectRelationship(
        relationship_type=EffectRelationshipType.REQUIRES,
        source_effect="fictional_gated_effect",
        target_effect="",
        condition="fictional_condition_a",
    )
    requires_b = EffectRelationship(
        relationship_type=EffectRelationshipType.REQUIRES,
        source_effect="fictional_gated_effect",
        target_effect="",
        condition="fictional_condition_b",
    )

    result = apply_relationships(
        [base],
        [requires_a, requires_b],
        frozenset({"fictional_condition_a", "fictional_condition_b"}),
    )

    assert result[0].eligible is True


def test_multiple_required_conditions_one_unmet_makes_ineligible():
    base = EffectVariant(
        name="fictional_gated_effect",
        layer=EffectLayer.CAST,
        source="Fictional Skill",
    )
    requires_a = EffectRelationship(
        relationship_type=EffectRelationshipType.REQUIRES,
        source_effect="fictional_gated_effect",
        target_effect="",
        condition="fictional_condition_a",
    )
    requires_b = EffectRelationship(
        relationship_type=EffectRelationshipType.REQUIRES,
        source_effect="fictional_gated_effect",
        target_effect="",
        condition="fictional_condition_b",
    )

    # Only condition A is present - B is missing, so the AND fails.
    result = apply_relationships(
        [base],
        [requires_a, requires_b],
        frozenset({"fictional_condition_a"}),
    )

    assert result[0].eligible is False
    # Still preserved as evidence.
    assert result[0].name == "fictional_gated_effect"


# ---------------------------------------------------------------------
# 6-8. MODIFIES / EXTENDS_DURATION / INCREASES_PROC_CHANCE
#      (baseline behavior confirmed already in test_effect_relationship.py;
#       here we confirm they still see triggered effects too.)
# ---------------------------------------------------------------------


def test_modifies_applies_to_a_triggered_effect():
    source = EffectVariant(
        name="fictional_ultimate_cast",
        layer=EffectLayer.ULTIMATE,
        source="Fictional Ultimate",
    )
    trigger = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_ultimate_cast",
        target_effect="fictional_proc_buff",
        magnitude_delta=100.0,
    )
    modifies = EffectRelationship(
        relationship_type=EffectRelationshipType.MODIFIES,
        source_effect="fictional_ultimate_cast",
        target_effect="fictional_proc_buff",
        magnitude_delta=25.0,
    )

    result = apply_relationships([source], [trigger, modifies])
    resolved = {effect.name: effect for effect in result}

    assert resolved["fictional_proc_buff"].magnitude == 125.0


# ---------------------------------------------------------------------
# 9. Chained triggers (proc chains)
# ---------------------------------------------------------------------


def test_chained_triggers_resolve_without_hardcoding_names():
    effect_a = EffectVariant(
        name="fictional_effect_a",
        layer=EffectLayer.CAST,
        source="Fictional Source A",
    )
    a_triggers_b = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_effect_a",
        target_effect="fictional_effect_b",
    )
    b_triggers_c = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_effect_b",
        target_effect="fictional_effect_c",
    )

    # Deliberately supplied out of causal order, to prove the chain
    # doesn't depend on relationship ordering.
    result = apply_relationships([effect_a], [b_triggers_c, a_triggers_b])
    names = {effect.name for effect in result}

    assert names == {
        "fictional_effect_a",
        "fictional_effect_b",
        "fictional_effect_c",
    }

    by_name = {effect.name: effect for effect in result}
    assert by_name["fictional_effect_c"].trigger == "fictional_effect_b"
    assert by_name["fictional_effect_c"].source == "fictional_effect_b"


def test_chain_does_not_fire_past_an_ineligible_link():
    effect_a = EffectVariant(
        name="fictional_effect_a",
        layer=EffectLayer.CAST,
        source="Fictional Source A",
    )
    a_triggers_b = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_effect_a",
        target_effect="fictional_effect_b",
        condition="fictional_unmet_condition",
    )
    b_triggers_c = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_effect_b",
        target_effect="fictional_effect_c",
    )

    result = apply_relationships(
        [effect_a], [a_triggers_b, b_triggers_c], frozenset()
    )
    names = {effect.name for effect in result}

    assert "fictional_effect_b" not in names
    assert "fictional_effect_c" not in names


# ---------------------------------------------------------------------
# 10. Duplicate trigger prevention (+ stacking interaction, 12/13)
# ---------------------------------------------------------------------


def test_duplicate_trigger_prevention_for_unique_effect():
    ultimate_cast = EffectVariant(
        name="fictional_ultimate_cast",
        layer=EffectLayer.ULTIMATE,
        source="Fictional Ultimate",
    )
    already_present = EffectVariant(
        name="fictional_unique_proc",
        layer=EffectLayer.PROC,
        source="Some Other Source",
        stacking=StackingBehavior.UNIQUE,
    )
    trigger = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_ultimate_cast",
        target_effect="fictional_unique_proc",
    )

    result = apply_relationships([ultimate_cast, already_present], [trigger])
    matching = [e for e in result if e.name == "fictional_unique_proc"]

    assert len(matching) == 1
    assert matching[0].source == "Some Other Source"


def test_stacking_effect_allows_multiple_independent_trigger_instances():
    ultimate_cast = EffectVariant(
        name="fictional_ultimate_cast",
        layer=EffectLayer.ULTIMATE,
        source="Fictional Ultimate",
    )
    already_present = EffectVariant(
        name="fictional_stacking_proc",
        layer=EffectLayer.PROC,
        source="Some Other Source",
        stacking=StackingBehavior.STACKS,
    )
    trigger = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_ultimate_cast",
        target_effect="fictional_stacking_proc",
        stacking=StackingBehavior.STACKS,
    )

    result = apply_relationships([ultimate_cast, already_present], [trigger])
    matching = [e for e in result if e.name == "fictional_stacking_proc"]

    assert len(matching) == 2
    assert {e.source for e in matching} == {
        "Some Other Source",
        "fictional_ultimate_cast",
    }


def test_same_stacking_trigger_does_not_re_fire_twice_from_same_source():
    """
    Re-running apply_relationships-style resolution over an already
    triggered STACKS effect from the same relationship source should not
    keep growing instances without bound.
    """
    ultimate_cast = EffectVariant(
        name="fictional_ultimate_cast",
        layer=EffectLayer.ULTIMATE,
        source="Fictional Ultimate",
    )
    trigger = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_ultimate_cast",
        target_effect="fictional_stacking_proc",
        stacking=StackingBehavior.STACKS,
    )

    # Two identical TRIGGERS relationships from the same source - this
    # must not produce two instances credited to the same source.
    result = apply_relationships([ultimate_cast], [trigger, trigger])
    matching = [e for e in result if e.name == "fictional_stacking_proc"]

    assert len(matching) == 1


# ---------------------------------------------------------------------
# 11. REQUIRES affecting eligibility
# ---------------------------------------------------------------------


def test_requires_makes_effect_ineligible_when_prerequisite_effect_absent():
    dependent = EffectVariant(
        name="fictional_minor_brittle",
        layer=EffectLayer.PROC,
        source="Fictional Frost Source",
    )
    requires = EffectRelationship(
        relationship_type=EffectRelationshipType.REQUIRES,
        source_effect="fictional_minor_brittle",
        target_effect="fictional_ice_staff_active",
    )

    result = apply_relationships([dependent], [requires])

    assert result[0].eligible is False


def test_requires_effect_is_eligible_when_prerequisite_effect_present():
    dependent = EffectVariant(
        name="fictional_minor_brittle",
        layer=EffectLayer.PROC,
        source="Fictional Frost Source",
    )
    prerequisite = EffectVariant(
        name="fictional_ice_staff_active",
        layer=EffectLayer.PASSIVE,
        source="Fictional Ice Staff",
    )
    requires = EffectRelationship(
        relationship_type=EffectRelationshipType.REQUIRES,
        source_effect="fictional_minor_brittle",
        target_effect="fictional_ice_staff_active",
    )

    result = apply_relationships([dependent, prerequisite], [requires])
    resolved = {effect.name: effect for effect in result}

    assert resolved["fictional_minor_brittle"].eligible is True


# ---------------------------------------------------------------------
# 12/13. Stacking vs UNIQUE preservation on base (non-triggered) effects
# ---------------------------------------------------------------------


def test_stacking_metadata_is_preserved_through_relationship_resolution():
    stacking_effect = EffectVariant(
        name="fictional_stacking_dot",
        layer=EffectLayer.CAST,
        source="Fictional DOT Source",
        stacking=StackingBehavior.STACKS,
        magnitude=50.0,
    )

    result = apply_relationships([stacking_effect], [])

    assert result[0].stacking == StackingBehavior.STACKS


def test_unique_metadata_is_preserved_through_relationship_resolution():
    unique_effect = EffectVariant(
        name="fictional_unique_buff",
        layer=EffectLayer.CAST,
        source="Fictional Buff Source",
        stacking=StackingBehavior.UNIQUE,
    )

    result = apply_relationships([unique_effect], [])

    assert result[0].stacking == StackingBehavior.UNIQUE


# ---------------------------------------------------------------------
# 14-17. Preservation of source/provider, magnitude, duration, chance
# ---------------------------------------------------------------------


def test_source_evidence_preserved_when_modifies_applies():
    base = EffectVariant(
        name="fictional_weapon_damage",
        layer=EffectLayer.SLOTTED,
        source="Original Glyph Source",
        magnitude=100.0,
    )
    presence = EffectVariant(
        name="fictional_item_equipped",
        layer=EffectLayer.PROC,
        source="Fictional Item",
    )
    modifies = EffectRelationship(
        relationship_type=EffectRelationshipType.MODIFIES,
        source_effect="fictional_item_equipped",
        target_effect="fictional_weapon_damage",
        magnitude_delta=50.0,
    )

    result = apply_relationships([base, presence], [modifies])
    resolved = {effect.name: effect for effect in result}

    assert resolved["fictional_weapon_damage"].source == "Original Glyph Source"
    assert resolved["fictional_weapon_damage"].magnitude == 150.0


def test_magnitude_duration_and_chance_all_preserved_independently():
    base = EffectVariant(
        name="fictional_multi_attr_effect",
        layer=EffectLayer.PROC,
        source="Fictional Source",
        magnitude=10.0,
        duration=5.0,
        chance=0.3,
    )
    presence = EffectVariant(
        name="fictional_item_equipped",
        layer=EffectLayer.PROC,
        source="Fictional Item",
    )
    extend = EffectRelationship(
        relationship_type=EffectRelationshipType.EXTENDS_DURATION,
        source_effect="fictional_item_equipped",
        target_effect="fictional_multi_attr_effect",
        magnitude_delta=2.0,
    )
    increase_chance = EffectRelationship(
        relationship_type=EffectRelationshipType.INCREASES_PROC_CHANCE,
        source_effect="fictional_item_equipped",
        target_effect="fictional_multi_attr_effect",
        magnitude_delta=0.1,
    )

    result = apply_relationships([base, presence], [extend, increase_chance])
    resolved = {effect.name: effect for effect in result}

    effect = resolved["fictional_multi_attr_effect"]
    assert effect.magnitude == 10.0  # untouched by these relationship types
    assert effect.duration == 7.0
    assert effect.chance == 0.4


# ---------------------------------------------------------------------
# 18. Relationship condition preservation
# ---------------------------------------------------------------------


def test_triggered_effect_preserves_its_gating_condition():
    source = EffectVariant(
        name="fictional_ultimate_cast",
        layer=EffectLayer.ULTIMATE,
        source="Fictional Ultimate",
    )
    trigger = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_ultimate_cast",
        target_effect="fictional_conditional_proc",
        condition="fictional_set_equipped_on_back_bar",
    )

    result = apply_relationships([source], [trigger])
    resolved = {effect.name: effect for effect in result}

    assert (
        resolved["fictional_conditional_proc"].condition
        == "fictional_set_equipped_on_back_bar"
    )


# ---------------------------------------------------------------------
# 19. Regression through character capability resolution
# ---------------------------------------------------------------------


def test_character_capability_resolution_regression_without_context():
    build = _build_with_effect(
        EffectVariant(
            name="fictional_group_buff",
            layer=EffectLayer.SLOTTED,
            source="Fictional Skill",
            magnitude=300,
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
        )
    )

    registry = CharacterCapabilityResolver().resolve(build, BarId.FRONT)
    effects = registry.all()

    assert len(effects) == 1
    assert effects[0].name == "fictional_group_buff"


def test_character_capability_resolution_excludes_ineligible_conditional_effect():
    build = _build_with_effect(
        EffectVariant(
            name="fictional_conditional_group_buff",
            layer=EffectLayer.SLOTTED,
            source="Fictional Skill",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
            condition="fictional_unmet_condition",
        )
    )

    registry = CharacterCapabilityResolver().resolve(
        build, BarId.FRONT, condition_context=frozenset()
    )

    assert registry.all() == ()


def test_character_capability_resolution_includes_satisfied_conditional_effect():
    build = _build_with_effect(
        EffectVariant(
            name="fictional_conditional_group_buff",
            layer=EffectLayer.SLOTTED,
            source="Fictional Skill",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
            condition="fictional_met_condition",
        )
    )

    registry = CharacterCapabilityResolver().resolve(
        build,
        BarId.FRONT,
        condition_context=frozenset({"fictional_met_condition"}),
    )

    assert {effect.name for effect in registry.all()} == {
        "fictional_conditional_group_buff"
    }


# ---------------------------------------------------------------------
# 20. Regression through roster capability resolution
# ---------------------------------------------------------------------


def test_roster_capability_resolution_regression_without_relationships():
    healer = _build_with_effect(
        EffectVariant(
            name="fictional_group_buff",
            layer=EffectLayer.SLOTTED,
            source="Fictional Skill",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
        )
    )
    healer = CharacterBuild(
        name="Healer One",
        character_class=healer.character_class,
        role=Role.HEALER,
        armor=healer.armor,
        front_bar=healer.front_bar,
    )

    capabilities = RosterCapabilityResolver().resolve(
        [healer], {"Healer One": BarId.FRONT}
    )

    assert set(capabilities) == {"fictional_group_buff"}
    assert len(capabilities["fictional_group_buff"]) == 1


def test_roster_capability_resolution_applies_shared_condition_context():
    build = _build_with_effect(
        EffectVariant(
            name="fictional_conditional_group_buff",
            layer=EffectLayer.SLOTTED,
            source="Fictional Skill",
            target_type=SupportTargetType.GROUP,
            category=SupportEffectCategory.BUFF,
            condition="fictional_encounter_fact",
        )
    )
    character = CharacterBuild(
        name="Healer One",
        character_class=build.character_class,
        role=Role.HEALER,
        armor=build.armor,
        front_bar=build.front_bar,
    )

    capabilities_without_fact = RosterCapabilityResolver().resolve(
        [character],
        {"Healer One": BarId.FRONT},
        condition_context=frozenset(),
    )
    capabilities_with_fact = RosterCapabilityResolver().resolve(
        [character],
        {"Healer One": BarId.FRONT},
        condition_context=frozenset({"fictional_encounter_fact"}),
    )

    assert "fictional_conditional_group_buff" not in capabilities_without_fact
    assert "fictional_conditional_group_buff" in capabilities_with_fact
