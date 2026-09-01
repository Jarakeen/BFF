from minmax.skill_component_effect_relationship import (
    SkillComponentEffectRelationshipType,
    canonical_effect_identity,
    extract_explicit_effect_applications,
)


def test_canonical_effect_identity_matches_effect_variant_style():
    assert canonical_effect_identity("Minor Brittle") == "minor_brittle"
    assert canonical_effect_identity("Off-Balance") == "off_balance"


def test_explicit_status_application_becomes_component_relationship():
    relationships = extract_explicit_effect_applications(
        skill_rank_id=4474,
        coefficient_number=1,
        fragment=(
            "The searing metal deals $1 Flame Damage, applies the Burning status "
            "effect, and taunts them for 15 seconds."
        ),
        known_effect_names=("Burning", "Chilled"),
    )

    assert len(relationships) == 1
    relationship = relationships[0]
    assert relationship.skill_rank_id == 4474
    assert relationship.coefficient_number == 1
    assert relationship.relationship_type is SkillComponentEffectRelationshipType.APPLIES
    assert relationship.target_effect == "burning"
    assert relationship.source_effect_name == "Burning"
    assert "applies the Burning status effect" in relationship.evidence


def test_named_effect_mention_without_application_is_not_promoted():
    relationships = extract_explicit_effect_applications(
        skill_rank_id=10,
        coefficient_number=1,
        fragment="Deal $1 Frost Damage to an enemy affected by Chilled.",
        known_effect_names=("Chilled",),
    )

    assert relationships == ()


def test_unknown_effect_name_is_not_invented_from_tooltip_text():
    relationships = extract_explicit_effect_applications(
        skill_rank_id=10,
        coefficient_number=1,
        fragment="Deal $1 Flame Damage and apply Imaginary Doom to the target.",
        known_effect_names=("Burning", "Chilled"),
    )

    assert relationships == ()


def test_inflicts_known_effect_is_supported_without_temporal_inference():
    relationships = extract_explicit_effect_applications(
        skill_rank_id=10,
        coefficient_number=2,
        fragment="The strike inflicts Chilled and deals $2 Frost Damage.",
        known_effect_names=("Chilled",),
    )

    assert len(relationships) == 1
    assert relationships[0].target_effect == "chilled"
    assert relationships[0].relationship_type is SkillComponentEffectRelationshipType.APPLIES
