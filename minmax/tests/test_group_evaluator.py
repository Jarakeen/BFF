from minmax.group_effects import GroupEffect
from minmax.group_evaluator import GroupEvaluator
from minmax.roster import RosterCandidate
from minmax.role import Role


def test_group_damage_includes_personal_damage():

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

    result = GroupEvaluator().evaluate(roster)

    assert result.group_damage == 190


def test_group_damage_includes_damage_amplification():

    support = RosterCandidate(
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
    )

    dd = RosterCandidate(
        name="DD",
        role=Role.DD,
        class_name="Nightblade",
        personal_damage=100,
    )

    result = GroupEvaluator().evaluate(
        [support, dd]
    )

    assert result.group_damage == 190


def test_group_effect_respects_uptime():

    support = RosterCandidate(
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
                uptime=0.5,
            ),
        ),
    )

    dd = RosterCandidate(
        name="DD",
        role=Role.DD,
        class_name="Nightblade",
        personal_damage=100,
    )

    result = GroupEvaluator().evaluate(
        [support, dd]
    )

    assert result.group_damage == 185


def test_effect_contribution_shows_provider_recipients_and_damage():
    """Verify that GroupEffectContribution records exact recipients and damage."""

    support = RosterCandidate(
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
    )

    dd1 = RosterCandidate(
        name="DD One",
        role=Role.DD,
        class_name="Nightblade",
        personal_damage=100,
    )

    dd2 = RosterCandidate(
        name="DD Two",
        role=Role.DD,
        class_name="Sorcerer",
        personal_damage=90,
    )

    result = GroupEvaluator().evaluate([support, dd1, dd2])

    # Should have exactly one effect contribution
    assert len(result.effect_contributions) == 1

    contrib = result.effect_contributions[0]
    assert contrib.source_name == "Support"
    assert contrib.effect_type == "damage_amplification"
    assert contrib.value == 10.0
    assert contrib.uptime == 1.0
    assert set(contrib.recipient_names) == {"DD One", "DD Two"}
    # 100 * 10 / 100 * 1.0 + 90 * 10 / 100 * 1.0 = 10 + 9 = 19
    assert contrib.damage_added == 19.0


def test_player_supported_damage_sums_to_group_damage():
    """Verify that sum of supported damage equals group_damage."""

    support = RosterCandidate(
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
    )

    dd1 = RosterCandidate(
        name="DD One",
        role=Role.DD,
        class_name="Nightblade",
        personal_damage=100,
    )

    dd2 = RosterCandidate(
        name="DD Two",
        role=Role.DD,
        class_name="Sorcerer",
        personal_damage=90,
    )

    result = GroupEvaluator().evaluate([support, dd1, dd2])

    # Sum all supported damage from contributions
    total_supported = sum(
        contrib.supported_damage
        for contrib in result.player_contributions
    )

    assert total_supported == result.group_damage
    # Support: 80, DD One: 100 + 10, DD Two: 90 + 9 = 289
    assert result.group_damage == 289


def test_unresolved_effects_recorded():
    """Verify that unsupported effect types are recorded as unresolved."""

    support = RosterCandidate(
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
    )

    tank = RosterCandidate(
        name="Tank",
        role=Role.TANK,
        class_name="Dragonknight",
        personal_damage=50,
    )

    result = GroupEvaluator().evaluate([support, tank])

    # Should have one unresolved effect
    assert len(result.unresolved_effects) == 1
    assert "healing_support" in result.unresolved_effects[0]
    assert "Support" in result.unresolved_effects[0]