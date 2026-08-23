from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.effect_relationship import (
    EffectRelationship,
    EffectRelationshipType,
    apply_relationships,
)

# These tests exercise the generic EffectRelationship engine mechanics
# only (duration extension, triggering, chance modification, magnitude
# modification). They use deliberately fictional source/effect names
# precisely so they cannot be mistaken for verified ESO facts - for
# that, see minmax/tests/test_character_build_real_data_integration.py,
# which drives the same engine with real, traced repository data.


def test_generic_duration_modification():
    base = EffectVariant(
        name="tracked_group_buff",
        layer=EffectLayer.CAST,
        source="Fictional Support Skill",
        duration=20.0,
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.EXTENDS_DURATION,
        source_effect="fictional_item_equipped",
        target_effect="tracked_group_buff",
        magnitude_delta=6.0,
    )
    presence_marker = EffectVariant(
        name="fictional_item_equipped",
        layer=EffectLayer.PROC,
        source="Fictional Item",
    )

    result = apply_relationships([base, presence_marker], [relationship])
    resolved = {effect.name: effect for effect in result}

    assert resolved["tracked_group_buff"].duration == 26.0


def test_relationship_does_not_apply_without_its_source_present():
    base = EffectVariant(
        name="tracked_group_buff",
        layer=EffectLayer.CAST,
        source="Fictional Support Skill",
        duration=20.0,
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.EXTENDS_DURATION,
        source_effect="fictional_item_equipped",
        target_effect="tracked_group_buff",
        magnitude_delta=6.0,
    )

    result = apply_relationships([base], [relationship])
    assert result[0].duration == 20.0


def test_generic_effect_trigger():
    """
    Exercises TRIGGERS producing a support effect that was not otherwise
    present. Uses a fictional ultimate/effect pair - no real ESO
    ultimate-to-set-proc relationship is asserted here or anywhere in
    the generic engine (see the real-data integration tests for what
    actually is traced from repository data).
    """
    ultimate_cast = EffectVariant(
        name="fictional_ultimate_cast",
        layer=EffectLayer.ULTIMATE,
        source="Fictional Ultimate Skill",
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_ultimate_cast",
        target_effect="fictional_set_proc_buff",
        condition="fictional_set_equipped_on_back_bar",
    )

    result = apply_relationships([ultimate_cast], [relationship])
    names = {effect.name for effect in result}

    assert "fictional_set_proc_buff" in names


def test_trigger_does_not_duplicate_an_existing_effect():
    ultimate_cast = EffectVariant(
        name="fictional_ultimate_cast",
        layer=EffectLayer.ULTIMATE,
        source="Fictional Ultimate Skill",
    )
    already_present = EffectVariant(
        name="fictional_set_proc_buff", layer=EffectLayer.PROC, source="Some Other Source"
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="fictional_ultimate_cast",
        target_effect="fictional_set_proc_buff",
    )

    result = apply_relationships([ultimate_cast, already_present], [relationship])
    matching_instances = [
        effect for effect in result if effect.name == "fictional_set_proc_buff"
    ]

    assert len(matching_instances) == 1
    assert matching_instances[0].source == "Some Other Source"


def test_generic_proc_chance_modification():
    base = EffectVariant(
        name="fictional_status_effect",
        layer=EffectLayer.PROC,
        source="Fictional Status Skill",
        chance=0.5,
    )
    presence_marker = EffectVariant(
        name="fictional_item_equipped_b", layer=EffectLayer.PROC, source="Fictional Item B"
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.INCREASES_PROC_CHANCE,
        source_effect="fictional_item_equipped_b",
        target_effect="fictional_status_effect",
        magnitude_delta=0.25,
    )

    result = apply_relationships([base, presence_marker], [relationship])
    resolved = {effect.name: effect for effect in result}

    assert resolved["fictional_status_effect"].chance == 0.75


def test_generic_effect_modification():
    base = EffectVariant(
        name="weapon_damage_flat", layer=EffectLayer.SLOTTED, source="Glyph", magnitude=100
    )
    presence_marker = EffectVariant(
        name="some_buff_source_equipped", layer=EffectLayer.PROC, source="Some Item"
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.MODIFIES,
        source_effect="some_buff_source_equipped",
        target_effect="weapon_damage_flat",
        magnitude_delta=25,
    )

    result = apply_relationships([base, presence_marker], [relationship])
    resolved = {effect.name: effect for effect in result}

    assert resolved["weapon_damage_flat"].magnitude == 125
