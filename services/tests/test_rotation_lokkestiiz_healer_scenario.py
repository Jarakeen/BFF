from services.rotation_lokkestiiz_healer_scenario import (
    build_magrat_df_healer_lokkestiiz_scenario,
)


def test_lokkestiiz_scenario_uses_three_canonical_flight_cycles() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    assert scenario.execution.requested_cycles == 3
    assert scenario.execution.canonical_flight_health_thresholds == (80, 50, 20)
    assert not any(
        "requested execution cycle count" in item
        for item in scenario.execution.unresolved
    )


def test_lokkestiiz_scenario_replaces_winters_revenge_with_elemental_blockade() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    assert len(scenario.skill_replacements) == 1
    replacement = scenario.skill_replacements[0]
    assert replacement.bar == "back"
    assert replacement.outgoing_semantic_id == "winters_revenge"
    assert replacement.incoming_semantic_id == "elemental_blockade"


def test_lokkestiiz_scenario_does_not_mutate_base_build_definition() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    assert "elemental_blockade" in scenario.execution.required_skill_ids
    assert "winters_revenge" not in scenario.execution.required_skill_ids
