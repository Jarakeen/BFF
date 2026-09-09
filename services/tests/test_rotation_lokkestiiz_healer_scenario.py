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


def test_lokkestiiz_scenario_selects_aggressive_horn_for_each_landing() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    assert scenario.selected_ultimate_semantic_id == "aggressive_horn"


def test_lokkestiiz_scenario_models_horn_readiness_as_affordability_not_attack_count() -> None:
    scenario = build_magrat_df_healer_lokkestiiz_scenario()

    assert not any("light-attack count" in item for item in scenario.unresolved)
    readiness = next(
        item for item in scenario.unresolved
        if "Aggressive Horn affordability at each landing" in item
    )
    assert "landing clock windows" in readiness
    assert "base-combat Ultimate-generation window" in readiness
    assert scenario.ready_for_clock_scheduling is False
