from services.rotation_lokkestiiz_healer_execution_profile import (
    RotationExecutionRequirementKind,
    build_magrat_df_healer_lokkestiiz_profile,
)


def _stage(profile, key):
    return next(stage for stage in profile.stages if stage.key == key)


def _requirement(stage, key):
    return next(item for item in stage.requirements if item.key == key)


def test_profile_captures_real_magrat_lokkestiiz_execution_contract() -> None:
    profile = build_magrat_df_healer_lokkestiiz_profile()

    assert profile.character_name == "Magrat"
    assert profile.build_name == "DF Healer"
    assert profile.encounter_id == "lokkestiiz"
    assert profile.requested_cycles == 4
    assert profile.canonical_flight_health_thresholds == (80, 50, 20)
    assert profile.canonical_flight_count == 3

    landing = _stage(profile, "landing")
    assert _requirement(landing, "landing_ultimate").minimum_casts == 1
    assert _requirement(landing, "landing_ultimate").semantic_id == "selected_ultimate"
    assert _requirement(landing, "landing_elemental_susceptibility").semantic_id == "elemental_susceptibility"
    assert _requirement(landing, "landing_elemental_blockade").semantic_id == "elemental_blockade"

    brittle = _requirement(landing, "damageable_major_brittle")
    assert brittle.kind is RotationExecutionRequirementKind.EFFECT
    assert brittle.target == "lokkestiiz"
    assert brittle.timing == "boss_damageable_non_immune_windows"

    light_attacks = _requirement(landing, "ultimate_regeneration_light_attacks")
    assert light_attacks.kind is RotationExecutionRequirementKind.LIGHT_ATTACK
    assert light_attacks.minimum_casts is None
    assert "runtime Ultimate evidence" in light_attacks.notes


def test_profile_preserves_exact_ice_cage_and_static_phase_cast_requirements() -> None:
    profile = build_magrat_df_healer_lokkestiiz_profile()

    cage_one = _stage(profile, "ice_cage_one")
    assert _requirement(cage_one, "cage_one_budding_seeds").minimum_casts == 1
    assert _requirement(cage_one, "cage_one_illustrious_healing").minimum_casts == 1
    assert _requirement(cage_one, "cage_one_combat_prayer").minimum_casts == 5

    cage_two = _stage(profile, "ice_cage_two")
    assert _requirement(cage_two, "cage_two_budding_seeds").minimum_casts == 1
    assert _requirement(cage_two, "cage_two_illustrious_healing").minimum_casts == 1
    assert _requirement(cage_two, "cage_two_combat_prayer").minimum_casts == 2

    add_phase = _stage(profile, "add_phase")
    supplemental = _requirement(add_phase, "supplemental_add_phase_healing")
    assert supplemental.kind is RotationExecutionRequirementKind.HEALING_OUTCOME
    assert supplemental.minimum_casts is None

    static = _stage(profile, "static_phase")
    assert _requirement(static, "static_budding_seeds").minimum_casts == 1
    assert _requirement(static, "static_illustrious_healing").minimum_casts == 1
    assert _requirement(static, "static_energy_orb").minimum_casts == 1
    assert _requirement(static, "static_combat_prayer").minimum_casts is None
    assert "several" in _requirement(static, "static_combat_prayer").notes


def test_profile_keeps_timing_and_flight_count_conflicts_explicit() -> None:
    profile = build_magrat_df_healer_lokkestiiz_profile()

    assert profile.ready_for_clock_scheduling is False
    assert any("requested=4, canonical=3" in item for item in profile.unresolved)
    assert any("clock windows" in item for item in profile.unresolved)
    assert any("light-attack count" in item for item in profile.unresolved)
    assert any("qualitative ('several')" in item for item in profile.unresolved)


def test_matching_cycle_count_removes_only_the_cycle_count_conflict() -> None:
    profile = build_magrat_df_healer_lokkestiiz_profile(requested_cycles=3)

    assert not any("requested execution cycle count" in item for item in profile.unresolved)
    assert any("clock windows" in item for item in profile.unresolved)
    assert profile.ready_for_clock_scheduling is False


def test_required_skill_ids_are_semantic_deduplicated_and_do_not_include_effects_or_outcomes() -> None:
    profile = build_magrat_df_healer_lokkestiiz_profile()

    assert profile.required_skill_ids == (
        "elemental_susceptibility",
        "elemental_blockade",
        "budding_seeds",
        "illustrious_healing",
        "combat_prayer",
        "energy_orb",
    )
