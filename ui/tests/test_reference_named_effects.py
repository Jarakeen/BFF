from ui.reference_named_effects import (
    build_named_effect_reference_entries,
    entry_from_named_effect,
)


def test_major_courage_exposes_u50_stat_semantics_and_minor_pair():
    entry = entry_from_named_effect("Major Courage")

    assert entry.entry_type == "Named Effect"
    assert ("Authority", "Canonical named-effect semantics") in entry.details
    assert ("Current modeled update", "U50") in entry.details
    assert any(
        label == "U50 semantics" and "Weapon Damage: 430 flat" in value and "Spell Damage: 430 flat" in value
        for label, value in entry.details
    )
    assert "Minor Courage" in entry.related
    assert "MAJOR" in entry.tags
    assert "STAT LAYER" in entry.tags


def test_component_owned_named_effect_does_not_invent_standing_stat_value():
    entry = entry_from_named_effect("Major Vulnerability")

    assert "COMPONENT LAYER" in entry.tags
    assert (
        "U50 semantics",
        "Owned by a component-specific calculation layer; no standing-stat value is defined here.",
    ) in entry.details
    assert ("Calculation layer", "Component-specific") in entry.details


def test_u51_changed_semantics_are_visible_without_mutating_u50_default():
    entry = entry_from_named_effect("Major Brutality")

    assert any(
        label == "U50 semantics" and "Weapon Damage: 20%" in value and "Spell Damage" not in value
        for label, value in entry.details
    )
    assert any(
        label == "U51 semantics" and "Weapon Damage: 20%" in value and "Spell Damage: 20%" in value
        for label, value in entry.details
    )


def test_removed_u51_named_effect_is_marked_without_aliasing_it():
    entry = entry_from_named_effect("Major Sorcery")

    assert ("U51 semantics", "Name is not present in the U51 canonical table.") in entry.details


def test_named_effect_catalog_contains_major_minor_and_component_entries():
    entries = build_named_effect_reference_entries()
    names = {entry.name for entry in entries}

    assert "Major Courage" in names
    assert "Minor Courage" in names
    assert "Major Vulnerability" in names
    assert "Minor Protection" in names
