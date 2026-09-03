from minmax.optimization_mode import OptimizationMode, policy_for_mode


def test_compare_mode_requires_two_teams_and_can_rank():
    policy = policy_for_mode(OptimizationMode.COMPARE)

    assert policy.uses_two_teams is True
    assert policy.ranks_result is True
    assert policy.allows_saved_players is True
    assert policy.allows_recruitment is True


def test_recruitment_mode_creates_requirements_not_saved_players():
    policy = policy_for_mode(OptimizationMode.RECRUIT)

    assert policy.action_label == "Generate Recruitment Plan"
    assert policy.allows_saved_players is False
    assert policy.allows_recruitment is True
    assert policy.ranks_result is False


def test_audit_mode_does_not_silently_add_recruitment_slots():
    policy = policy_for_mode(OptimizationMode.AUDIT)

    assert policy.allows_saved_players is True
    assert policy.allows_recruitment is False
    assert policy.ranks_result is False


def test_build_mode_supports_hybrid_team_generation():
    policy = policy_for_mode(OptimizationMode.BUILD)

    assert policy.uses_two_teams is False
    assert policy.allows_saved_players is True
    assert policy.allows_recruitment is True
    assert policy.ranks_result is True
