from services.gameplay_policy_service import GameplayPolicy
from ui.reference_data_model import (
    build_reference_entries,
    entry_from_policy,
    entry_types,
    source_scopes,
)


def _policy(**overrides):
    values = {
        "id": "standard_light_attack_weave_window",
        "role": "any",
        "content_type": ("trial", "raid"),
        "default_behavior": "shared_cadence_window",
        "subject": "light_attack_weaving",
        "confidence": "canonical",
        "summary": "A light attack and skill share the normal weave cadence window.",
        "exceptions": (),
        "affected_systems": ("rotation_builder", "performance_review"),
        "rationale": ("players weave attacks and skills rather than adding a second GCD",),
        "override_contexts": (),
        "modeling_requirements": ("do_not_add_an_extra_second",),
        "explanation_requirement": None,
    }
    values.update(overrides)
    return GameplayPolicy(**values)


def test_policy_entry_keeps_mechanics_and_practice_authority_explicit():
    entry = entry_from_policy(_policy())

    assert entry.name == "Light Attack Weaving"
    assert entry.entry_type == "Combat Rule"
    assert ("Authority", "Gameplay-practice policy") in entry.details
    assert ("Confidence", "Canonical") in entry.details
    assert "Gameplay policy: standard_light_attack_weave_window" in entry.evidence


def test_policy_entry_exposes_foundrydock_consumers_without_redefining_rule():
    entry = entry_from_policy(_policy())

    assert entry.used_by == ("Rotation Builder", "Performance / Raid Review")
    assert "rotation builder" in entry.search_text
    assert "performance / raid review" in entry.search_text


def test_policy_entry_surfaces_contextual_exceptions_and_field_notes():
    entry = entry_from_policy(
        _policy(
            id="dd_redundant_personal_heal",
            role="dd",
            subject="personal_heal_skill_slot",
            default_behavior="disfavor",
            exceptions=("portal_or_split_group_assignment",),
            rationale=("DD bar space has an opportunity cost",),
        )
    )

    assert entry.name == "DD Personal Heal Slot"
    assert "portal or split group assignment" in entry.detail_text()
    assert "Why players do this" in entry.field_note
    assert "opportunity cost" in entry.field_note


def test_reference_entries_are_sorted_and_filter_dimensions_are_derived():
    entries = build_reference_entries(
        (
            _policy(),
            _policy(
                id="healer_support_not_raw_hps",
                role="healer",
                subject="healer_optimization",
                default_behavior="require_balanced_objective",
            ),
        )
    )

    assert [entry.name for entry in entries] == ["Healer Support Objective", "Light Attack Weaving"]
    assert entry_types(entries) == ("Combat Rule", "Role")
    assert source_scopes(entries) == ("Global Combat", "Player")
