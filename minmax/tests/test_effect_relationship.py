from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.effect_relationship import (
    EffectRelationship,
    EffectRelationshipType,
    apply_relationships,
)


def test_generic_duration_modification():
    """
    Mirrors the shape of Jorvuld's Guidance (extends a supported effect's
    duration) without hard-coding Jorvuld's into the architecture.
    """
    base = EffectVariant(
        name="minor_toughness",
        layer=EffectLayer.CAST,
        source="Combat Prayer",
        duration=20.0,
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.EXTENDS_DURATION,
        source_effect="jorvulds_guidance_equipped",
        target_effect="minor_toughness",
        magnitude_delta=6.0,
    )
    presence_marker = EffectVariant(
        name="jorvulds_guidance_equipped",
        layer=EffectLayer.PROC,
        source="Jorvulds Guidance",
    )

    result = apply_relationships([base, presence_marker], [relationship])
    resolved = {effect.name: effect for effect in result}

    assert resolved["minor_toughness"].duration == 26.0


def test_relationship_does_not_apply_without_its_source_present():
    base = EffectVariant(
        name="minor_toughness", layer=EffectLayer.CAST, source="Combat Prayer", duration=20.0
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.EXTENDS_DURATION,
        source_effect="jorvulds_guidance_equipped",
        target_effect="minor_toughness",
        magnitude_delta=6.0,
    )

    result = apply_relationships([base], [relationship])
    assert result[0].duration == 20.0


def test_generic_effect_trigger():
    """
    Mirrors an Aggressive Horn-style trigger producing a support effect
    that was not otherwise present, without hard-coding Aggressive Horn.
    """
    ultimate_cast = EffectVariant(
        name="aggressive_horn_cast", layer=EffectLayer.ULTIMATE, source="Aggressive Horn"
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="aggressive_horn_cast",
        target_effect="major_slayer",
        condition="masters_architect_back_bar",
    )

    result = apply_relationships([ultimate_cast], [relationship])
    names = {effect.name for effect in result}

    assert "major_slayer" in names


def test_trigger_does_not_duplicate_an_existing_effect():
    ultimate_cast = EffectVariant(
        name="aggressive_horn_cast", layer=EffectLayer.ULTIMATE, source="Aggressive Horn"
    )
    already_present = EffectVariant(
        name="major_slayer", layer=EffectLayer.PROC, source="Some Other Source"
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.TRIGGERS,
        source_effect="aggressive_horn_cast",
        target_effect="major_slayer",
    )

    result = apply_relationships([ultimate_cast, already_present], [relationship])
    slayer_instances = [effect for effect in result if effect.name == "major_slayer"]

    assert len(slayer_instances) == 1
    assert slayer_instances[0].source == "Some Other Source"


def test_generic_proc_chance_modification():
    """
    Mirrors a Serpent's Disdain-style status-duration/chance modifier
    without hard-coding it into the architecture.
    """
    base = EffectVariant(
        name="poisoned_status",
        layer=EffectLayer.PROC,
        source="Poison Injection",
        chance=0.5,
    )
    presence_marker = EffectVariant(
        name="serpents_disdain_equipped", layer=EffectLayer.PROC, source="Serpents Disdain"
    )
    relationship = EffectRelationship(
        relationship_type=EffectRelationshipType.INCREASES_PROC_CHANCE,
        source_effect="serpents_disdain_equipped",
        target_effect="poisoned_status",
        magnitude_delta=0.25,
    )

    result = apply_relationships([base, presence_marker], [relationship])
    resolved = {effect.name: effect for effect in result}

    assert resolved["poisoned_status"].chance == 0.75


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
