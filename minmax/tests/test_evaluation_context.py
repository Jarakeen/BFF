from minmax.evaluation_context import EvaluationContext


def test_default_evaluation_context():
    context = EvaluationContext()

    assert context.fight_duration is None
    assert context.target_count == 1
    assert context.target_resistance is None


def test_evaluation_context_preserves_values():
    context = EvaluationContext(
        fight_duration=180.0,
        target_count=3,
        target_resistance=18_200.0,
    )

    assert context.fight_duration == 180.0
    assert context.target_count == 3
    assert context.target_resistance == 18_200.0