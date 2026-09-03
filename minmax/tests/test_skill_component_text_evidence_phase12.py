from minmax.skill_component_text_evidence import extract_component_text_evidence


def test_you_and_allies_periodic_heal_is_classified_as_aoe_hot() -> None:
    result = extract_component_text_evidence(
        "While the field grows, you and allies are healed for $2 Health every 1 second.",
        2,
    )

    assert result.effect_kind == "heal"
    assert result.is_dot is True
    assert result.is_aoe is True


def test_placeholder_health_over_duration_is_periodic_healing() -> None:
    result = extract_component_text_evidence(
        "An ally within the field can activate the Harvest synergy, healing for $3 Health over 5 seconds.",
        3,
    )

    assert result.effect_kind == "heal"
    assert result.is_dot is True
    assert result.is_aoe is False
