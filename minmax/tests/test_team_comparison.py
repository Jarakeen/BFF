from minmax.group_effects import GroupEffect
from minmax.group_evaluator import GroupEvaluator
from minmax.roster import RosterCandidate
from minmax.role import Role
from minmax.team_comparison import TeamComparison


def test_two_team_comparison_selects_higher_damage():
    """Verify that TeamComparison prefers the higher modeled composition damage."""

    baseline_roster = [
        RosterCandidate(
            name="DD One",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=100,
        ),
        RosterCandidate(
            name="DD Two",
            role=Role.DD,
            class_name="Sorcerer",
            personal_damage=90,
        ),
    ]

    candidate_roster = [
        RosterCandidate(
            name="DD One",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=105,  # Slightly higher
        ),
        RosterCandidate(
            name="DD Two",
            role=Role.DD,
            class_name="Sorcerer",
            personal_damage=95,  # Slightly higher
        ),
    ]

    baseline_eval = GroupEvaluator().evaluate(baseline_roster)
    candidate_eval = GroupEvaluator().evaluate(candidate_roster)

    comparison = TeamComparison(
        baseline_name="Baseline",
        candidate_name="Candidate",
        baseline_evaluation=baseline_eval,
        candidate_evaluation=candidate_eval,
    )

    assert comparison.rankable
    assert comparison.modeled_damage_delta == 10.0
    assert comparison.preferred_team_name == "Candidate"
    assert "Candidate wins" in comparison.explanation


def test_comparison_with_unresolved_effects_not_rankable():
    """Verify that comparison is not rankable when unresolved effects exist."""

    baseline_roster = [
        RosterCandidate(
            name="Support",
            role=Role.DD,
            class_name="Dragonknight",
            personal_damage=80,
            group_effects=(
                GroupEffect(
                    source="Support",
                    effect_type="healing_support",
                    value=50,
                    affected_roles=frozenset({Role.TANK}),
                    affects_source=False,
                ),
            ),
        ),
        RosterCandidate(
            name="DD",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=100,
        ),
    ]

    candidate_roster = [
        RosterCandidate(
            name="DD One",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=105,
        ),
        RosterCandidate(
            name="DD Two",
            role=Role.DD,
            class_name="Sorcerer",
            personal_damage=95,
        ),
    ]

    baseline_eval = GroupEvaluator().evaluate(baseline_roster)
    candidate_eval = GroupEvaluator().evaluate(candidate_roster)

    comparison = TeamComparison(
        baseline_name="Baseline",
        candidate_name="Candidate",
        baseline_evaluation=baseline_eval,
        candidate_evaluation=candidate_eval,
    )

    assert not comparison.rankable
    assert comparison.preferred_team_name is None
    assert "Cannot rank" in comparison.explanation
    assert "unresolved effects" in comparison.explanation


def test_comparison_declares_no_winner_on_tie():
    """Verify that comparison declares no winner when damage is equal."""

    roster = [
        RosterCandidate(
            name="DD One",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=100,
        ),
        RosterCandidate(
            name="DD Two",
            role=Role.DD,
            class_name="Sorcerer",
            personal_damage=90,
        ),
    ]

    eval1 = GroupEvaluator().evaluate(roster)
    eval2 = GroupEvaluator().evaluate(roster)

    comparison = TeamComparison(
        baseline_name="Team A",
        candidate_name="Team B",
        baseline_evaluation=eval1,
        candidate_evaluation=eval2,
    )

    assert comparison.rankable
    assert comparison.modeled_damage_delta == 0.0
    assert comparison.preferred_team_name is None
    assert "Tied" in comparison.explanation


def test_comparison_baseline_wins_on_lower_candidate():
    """Verify that baseline is preferred when it has higher damage."""

    baseline_roster = [
        RosterCandidate(
            name="DD One",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=110,
        ),
        RosterCandidate(
            name="DD Two",
            role=Role.DD,
            class_name="Sorcerer",
            personal_damage=100,
        ),
    ]

    candidate_roster = [
        RosterCandidate(
            name="DD One",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=105,
        ),
        RosterCandidate(
            name="DD Two",
            role=Role.DD,
            class_name="Sorcerer",
            personal_damage=90,
        ),
    ]

    baseline_eval = GroupEvaluator().evaluate(baseline_roster)
    candidate_eval = GroupEvaluator().evaluate(candidate_roster)

    comparison = TeamComparison(
        baseline_name="Baseline",
        candidate_name="Candidate",
        baseline_evaluation=baseline_eval,
        candidate_evaluation=candidate_eval,
    )

    assert comparison.rankable
    assert comparison.modeled_damage_delta < 0
    assert comparison.preferred_team_name == "Baseline"
    assert "Baseline wins" in comparison.explanation


def test_effect_contribution_affects_delta():
    """Verify that effect contributions impact the damage delta calculation."""

    baseline_roster = [
        RosterCandidate(
            name="DD One",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=100,
        ),
        RosterCandidate(
            name="DD Two",
            role=Role.DD,
            class_name="Sorcerer",
            personal_damage=90,
        ),
    ]

    candidate_roster = [
        RosterCandidate(
            name="Support",
            role=Role.DD,
            class_name="Dragonknight",
            personal_damage=80,
            group_effects=(
                GroupEffect(
                    source="Support",
                    effect_type="damage_amplification",
                    value=10,
                    affected_roles=frozenset({Role.DD}),
                    affects_source=False,
                ),
            ),
        ),
        RosterCandidate(
            name="DD One",
            role=Role.DD,
            class_name="Nightblade",
            personal_damage=100,
        ),
        RosterCandidate(
            name="DD Two",
            role=Role.DD,
            class_name="Sorcerer",
            personal_damage=90,
        ),
    ]

    baseline_eval = GroupEvaluator().evaluate(baseline_roster)
    candidate_eval = GroupEvaluator().evaluate(candidate_roster)

    comparison = TeamComparison(
        baseline_name="Baseline",
        candidate_name="Candidate",
        baseline_evaluation=baseline_eval,
        candidate_evaluation=candidate_eval,
    )

    # Baseline: 100 + 90 = 190
    # Candidate: 80 + 100 + 90 + (100*10/100 + 90*10/100) = 270 + 19 = 289
    # Delta: 289 - 190 = 99
    assert baseline_eval.group_damage == 190
    assert candidate_eval.group_damage == 289
    assert comparison.modeled_damage_delta == 99
    assert comparison.rankable
    assert comparison.preferred_team_name == "Candidate"
