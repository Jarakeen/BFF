from services.minmax.group_effects import GroupEffect
from services.minmax.group_evaluator import GroupEvaluator
from services.minmax.roster import RosterCandidate
from services.minmax.role import Role


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