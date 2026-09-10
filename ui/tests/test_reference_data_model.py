from services.combat_effect_reference_service import (
    CombatEffectInteractionReference,
    CombatEffectReference,
    CombatEffectTriggerReference,
)
from services.encounter_projection import (
    EncounterDefinition,
    EncounterMechanic,
    EncounterPhase,
    EncounterSource,
)
from services.gameplay_policy_service import GameplayPolicy
from ui.reference_data_model import (
    build_reference_entries,
    entry_from_combat_effect,
    entry_from_encounter_mechanic,
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


def _encounter(mechanic: EncounterMechanic) -> EncounterDefinition:
    return EncounterDefinition(
        encounter_id="test_boss",
        content_id="test_trial",
        name="Test Boss",
        difficulty_health=(("veteran", "1000000"),),
        source=EncounterSource(
            url="https://example.invalid/test-boss",
            page_title="Test Boss source",
            revision_id="12345",
            retrieved_at="2026-09-10",
            license="test",
        ),
        actors=(),
        mechanics=(mechanic,),
        phases=(
            EncounterPhase(
                phase_id="test_boss:phase:1",
                label="Execute",
                threshold="20%",
                description="Final phase",
            ),
        ),
        evidence_facts=(),
    )


def _mechanic(**overrides) -> EncounterMechanic:
    values = {
        "mechanic_id": "test_boss:canonical:crushing_darkness",
        "name": "Crushing Darkness",
        "description": "A dangerous encounter mechanic.",
        "interpretation_status": "reviewed",
        "mechanic_type": "raid_damage",
        "damage_type": "magic",
        "target_count": 4,
        "requires_movement": True,
        "requires_positioning": True,
        "requires_cleanse": False,
        "persistent_hazard": False,
        "failure_is_fatal": True,
        "interruptible": False,
        "requirement_subjects": (("movement", "player"),),
    }
    values.update(overrides)
    return EncounterMechanic(**values)


def _effect(**overrides) -> CombatEffectReference:
    values = {
        "effect_id": 2,
        "name": "Chilled",
        "category": "Status",
        "description": "Frost status effect.",
        "duration": 4.0,
        "tick_interval": None,
        "stack_max": None,
        "immunity_duration": None,
        "raw_source": "canonical row",
        "triggers": (
            CombatEffectTriggerReference(
                trigger_type="Damage",
                damage_type="Frost",
                weapon_requirement=None,
                condition=None,
                raw_source="ESO Wiki combat effects",
            ),
        ),
        "interactions": (
            CombatEffectInteractionReference(
                target_name="Minor Maim",
                interaction_type="Applies",
                condition=None,
                duration=4.0,
                target_value=5.0,
                target_unit="percent",
                target_scope="Target",
                raw_source="ESO Wiki combat effects",
            ),
        ),
    }
    values.update(overrides)
    return CombatEffectReference(**values)


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


def test_encounter_mechanic_entry_preserves_canonical_authority_and_known_fields():
    mechanic = _mechanic()
    entry = entry_from_encounter_mechanic(_encounter(mechanic), mechanic)

    assert entry.name == "Crushing Darkness — Test Boss"
    assert entry.entry_type == "Mechanic"
    assert entry.source_scope == "Trial"
    assert ("Authority", "Canonical encounter data") in entry.details
    assert ("Damage type", "magic") in entry.details
    assert ("Target count", "4") in entry.details
    assert ("Requires movement", "Yes") in entry.details
    assert ("Interruptible", "No") in entry.details
    assert "FATAL FAILURE" in entry.tags
    assert "The canonical record marks failure of this mechanic as fatal." in entry.death_note


def test_encounter_mechanic_entry_keeps_unknowns_explicit_instead_of_guessing():
    mechanic = _mechanic(
        damage_type=None,
        target_count=None,
        requires_movement=None,
        requires_positioning=None,
        requires_cleanse=None,
        persistent_hazard=None,
        failure_is_fatal=None,
        interruptible=None,
    )
    entry = entry_from_encounter_mechanic(_encounter(mechanic), mechanic)

    assert ("Damage type", "Not modeled") in entry.details
    assert ("Target count", "Not modeled") in entry.details
    assert ("Requires movement", "Not modeled") in entry.details
    assert ("Interruptible", "Not modeled") in entry.details
    assert "does not currently contain enough structured failure data" in entry.death_note
    assert "Gameplay-practice handling is not inferred" in entry.field_note


def test_combat_effect_entry_exposes_trigger_interaction_and_canonical_authority():
    entry = entry_from_combat_effect(_effect())

    assert entry.name == "Chilled"
    assert entry.entry_type == "Status Effect"
    assert entry.source_scope == "Global Combat"
    assert ("Authority", "Canonical combat-effect data") in entry.details
    assert ("Duration", "4 s") in entry.details
    assert "Frost damage" in entry.detail_text()
    assert "Applies Minor Maim" in entry.detail_text()
    assert entry.related == ("Minor Maim",)
    assert "Rotation Builder" in entry.used_by


def test_combat_effect_entry_keeps_missing_values_explicit():
    entry = entry_from_combat_effect(
        _effect(duration=None, triggers=(), interactions=())
    )

    assert ("Duration", "Not modeled") in entry.details
    assert ("Tick interval", "Not modeled") in entry.details
    assert entry.related == ()
    assert "Provider choice" in entry.field_note


def test_build_reference_entries_can_merge_policy_encounter_and_effect_records():
    mechanic = _mechanic()
    entries = build_reference_entries(
        (_policy(),),
        encounters=(_encounter(mechanic),),
        effects=(_effect(),),
    )

    assert [entry.name for entry in entries] == [
        "Chilled",
        "Crushing Darkness — Test Boss",
        "Light Attack Weaving",
    ]
    assert entry_types(entries) == ("Combat Rule", "Mechanic", "Status Effect")
    assert source_scopes(entries) == ("Global Combat", "Trial")
