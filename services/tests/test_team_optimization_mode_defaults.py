from minmax.optimization_mode import OptimizationMode, policy_for_mode
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


def test_optimize_defaults_preserve_composition_and_allow_build_changes() -> None:
    policy = policy_for_mode(OptimizationMode.BUILD)
    preset = defaults_for_mode(OptimizationMode.BUILD)

    assert policy.title == "Optimize Team"
    assert policy.action_label == "Optimize Team"
    assert preset.team_source == "Hybrid: Players + Recruitment"
    assert preset.lock_players
    assert preset.lock_roles
    assert preset.lock_classes
    assert not preset.keep_current_builds
    assert not preset.allow_role_swap
    assert preset.allow_gear_changes


def test_recruitment_defaults_remain_available_for_internal_compatibility() -> None:
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
