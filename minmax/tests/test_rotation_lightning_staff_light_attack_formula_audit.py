from tools.audit_rotation_lightning_staff_light_attack_formula import (
    audit_lightning_staff_light_attack_formula,
)


def test_shock_light_attack_contract_is_flagged_for_source_review() -> None:
    audit = audit_lightning_staff_light_attack_formula()

    assert audit.requires_source_review is True
    assert audit.suspicious_heavy_or_dot_inputs == (
        "skill_ha_damage",
        "set_ha_damage",
        "buff_empower",
        "dot_damage_done",
    )
    assert audit.missing_common_la_inputs == (
        "skill_la_damage",
        "set_la_damage",
        "direct_damage_done",
    )


def test_reference_common_inputs_prove_missing_la_family_terms_are_not_guessed() -> None:
    audit = audit_lightning_staff_light_attack_formula()

    assert "skill_la_damage" in audit.reference_common_inputs
    assert "set_la_damage" in audit.reference_common_inputs
    assert "direct_damage_done" in audit.reference_common_inputs
    assert "single_target_damage_done" in audit.reference_common_inputs
    assert "damage_done" in audit.reference_common_inputs
