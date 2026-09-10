from __future__ import annotations

from services.gameplay_policy_service import GameplayPolicyService, policy_ids


def test_registry_loads_known_role_practice_policies() -> None:
    service = GameplayPolicyService()

    assert "dd_redundant_personal_heal" in service.ids()
    assert "standard_light_attack_weave_window" in service.ids()


def test_dd_personal_heal_policy_is_contextual_not_absolute() -> None:
    policy = GameplayPolicyService().require("dd_redundant_personal_heal")

    assert policy.role == "dd"
    assert policy.default_behavior == "disfavor"
    assert "deliberate_range_separation_from_healers" in policy.exceptions
    assert "portal_or_split_group_assignment" in policy.exceptions
    assert policy.explanation_requirement


def test_dd_policy_is_available_to_rotation_and_team_consumers() -> None:
    service = GameplayPolicyService()

    rotation = service.find(
        role="dd",
        content_type="trial",
        affected_system="rotation_builder",
    )
    team = service.find(
        role="dd",
        content_type="trial",
        affected_system="team_optimization",
    )

    assert "dd_redundant_personal_heal" in policy_ids(rotation)
    assert "dd_redundant_personal_heal" in policy_ids(team)


def test_light_attack_weave_policy_applies_across_roles() -> None:
    service = GameplayPolicyService()

    for role in ("dd", "healer", "tank"):
        policies = service.find(
            role=role,
            content_type="trial",
            subject="light_attack_weaving",
        )
        assert policy_ids(policies) == ("standard_light_attack_weave_window",)


def test_light_attack_weave_does_not_consume_an_extra_full_second() -> None:
    policy = GameplayPolicyService().require("standard_light_attack_weave_window")

    assert policy.default_behavior == "shared_cadence_window"
    assert (
        "do_not_advance_the_rotation_clock_by_an_extra_full_second_for_the_light_attack"
        in policy.modeling_requirements
    )
    assert (
        "preserve_light_attack_as_an_explicit_combat_event_for_damage_and_trigger_resolution"
        in policy.modeling_requirements
    )
