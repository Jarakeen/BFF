import pytest

from services.minmax.evaluation_objective import (
    EvaluationObjective,
    ObjectiveWeights,
)


def test_default_weights_are_zero():
    weights = ObjectiveWeights()

    assert weights.damage == 0
    assert weights.healing == 0
    assert weights.survivability == 0
    assert weights.sustain == 0


def test_weight_for_returns_matching_weight():
    weights = ObjectiveWeights(
        damage=1.0,
        healing=2.0,
        survivability=3.0,
        sustain=4.0,
    )

    assert (
        weights.weight_for(EvaluationObjective.DAMAGE)
        == 1.0
    )

    assert (
        weights.weight_for(EvaluationObjective.HEALING)
        == 2.0
    )

    assert (
        weights.weight_for(EvaluationObjective.SURVIVABILITY)
        == 3.0
    )

    assert (
        weights.weight_for(EvaluationObjective.SUSTAIN)
        == 4.0
    )


def test_negative_weight_is_rejected():
    with pytest.raises(ValueError):
        ObjectiveWeights(damage=-1.0)