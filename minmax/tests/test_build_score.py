from minmax.build_evaluation import BuildEvaluation
from minmax.build_score import (
    BuildScore,
    score_build,
)
from minmax.combat_contribution import CombatContribution
from minmax.evaluation_objective import (
    ObjectiveWeights,
)


def make_evaluation(
    *,
    damage: float = 0.0,
    healing: float = 0.0,
) -> BuildEvaluation:
    contributions = []

    if damage:
        contributions.append(
            CombatContribution(
                source="Test Damage",
                effect_type="damage",
                raw_value=damage,
                uptime=1.0,
                effective_value=damage,
            )
        )

    if healing:
        contributions.append(
            CombatContribution(
                source="Test Healing",
                effect_type="health_restore",
                raw_value=healing,
                uptime=1.0,
                effective_value=healing,
            )
        )

    return BuildEvaluation(
        stats=None,
        combat_effects=(),
        combat_contributions=tuple(contributions),
    )


def test_score_build_returns_build_score():
    evaluation = make_evaluation(damage=1000)

    result = score_build(
        evaluation,
        ObjectiveWeights(damage=1.0),
    )

    assert isinstance(result, BuildScore)


def test_damage_is_used_as_damage_score():
    evaluation = make_evaluation(damage=2500)

    result = score_build(
        evaluation,
        ObjectiveWeights(damage=1.0),
    )

    assert result.damage == 2500


def test_weighted_damage_produces_total():
    evaluation = make_evaluation(damage=2500)

    result = score_build(
        evaluation,
        ObjectiveWeights(damage=2.0),
    )

    assert result.total == 5000


def test_healing_can_be_scored_independently():
    evaluation = make_evaluation(healing=1500)

    result = score_build(
        evaluation,
        ObjectiveWeights(healing=2.0),
    )

    assert result.healing == 1500
    assert result.total == 3000


def test_unsupported_dimensions_are_zero():
    evaluation = make_evaluation(damage=1000)

    result = score_build(
        evaluation,
        ObjectiveWeights(
            damage=1.0,
            survivability=10.0,
            sustain=10.0,
        ),
    )

    assert result.survivability == 0
    assert result.sustain == 0
    assert result.total == 1000