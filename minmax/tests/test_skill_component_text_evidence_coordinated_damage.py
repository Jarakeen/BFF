from minmax.skill_component_text_evidence import extract_component_text_evidence


PESTILENT = (
    "The Colossus smashes the ground three times over 3 seconds, "
    "dealing $1, $2, and $3 Disease Damage with the first, second, and third smash."
)


def test_coordinated_damage_list_resolves_first_component():
    evidence = extract_component_text_evidence(PESTILENT, 1)
    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "disease"
    assert evidence.is_dot is False


def test_coordinated_damage_list_resolves_middle_component():
    evidence = extract_component_text_evidence(PESTILENT, 2)
    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "disease"
    assert evidence.is_dot is False


def test_coordinated_damage_list_resolves_last_component():
    evidence = extract_component_text_evidence(PESTILENT, 3)
    assert evidence.effect_kind == "damage"
    assert evidence.damage_type == "disease"
    assert evidence.is_dot is False


def test_neighboring_placeholder_does_not_borrow_damage_type():
    text = "Heal for $1 Health. Then deal $2 Disease Damage."
    first = extract_component_text_evidence(text, 1)
    second = extract_component_text_evidence(text, 2)
    assert first.effect_kind == "heal"
    assert first.damage_type is None
    assert second.effect_kind == "damage"
    assert second.damage_type == "disease"
