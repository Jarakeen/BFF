from services.minmax.combat_context import CombatContext


def test_default_context():
    context = CombatContext()

    assert context.target is None
    assert context.active_conditions == set()
    assert context.elapsed_time == 0.0


def test_condition_can_be_active():
    context = CombatContext(
        active_conditions={"enemy_under_50_health"},
    )

    assert context.is_active("enemy_under_50_health")


def test_unknown_condition_is_inactive():
    context = CombatContext(
        active_conditions={"enemy_under_50_health"},
    )

    assert not context.is_active("enemy_full_health")


def test_target_is_preserved():
    context = CombatContext(
        target="boss",
    )

    assert context.target == "boss"


def test_elapsed_time_is_preserved():
    context = CombatContext(
        elapsed_time=12.5,
    )

    assert context.elapsed_time == 12.5