from minmax.optimization_mode import OptimizationMode
from ui.team_optimization_mode_defaults import defaults_for_mode


def test_audit_defaults_preserve_current_team() -> None:
    preset = defaults_for_mode(OptimizationMode.AUDIT)

    assert preset.team_source == "Saved Players Only"
    assert preset.lock_players
    assert preset.lock_roles
    assert preset.lock_classes
    assert preset.keep_current_builds
    assert not preset.allow_role_swap
    assert not preset.allow_gear_changes


def test_build_defaults_start_in_hybrid_and_allow_full_prescription() -> None:
    preset = defaults_for_mode(OptimizationMode.BUILD)

    assert preset.team_source == "Hybrid: Players + Recruitment"
    assert not preset.lock_players
    assert not preset.lock_roles
    assert not preset.lock_classes
    assert not preset.keep_current_builds
    assert preset.allow_role_swap
    assert preset.allow_gear_changes


def test_recruitment_defaults_start_with_recruitment_plan_only() -> None:
    preset = defaults_for_mode(OptimizationMode.RECRUIT)

    assert preset.team_source == "Recruitment Plan Only"
    assert not preset.lock_players
    assert not preset.keep_current_builds


def test_compare_defaults_preserve_selected_team_compositions() -> None:
    preset = defaults_for_mode(OptimizationMode.COMPARE)

    assert preset.team_source == "Hybrid: Players + Recruitment"
    assert preset.lock_players
    assert preset.lock_roles
    assert preset.lock_classes
    assert preset.keep_current_builds
    assert not preset.allow_role_swap
    assert not preset.allow_gear_changes
