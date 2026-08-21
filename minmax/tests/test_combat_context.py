from minmax.combat_context import CombatContext


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

def test_fight_duration_is_preserved():
    context = CombatContext(
        fight_duration=60.0,
    )

    assert context.fight_duration == 60.0


def test_remaining_time_is_calculated():
    context = CombatContext(
        elapsed_time=15.0,
        fight_duration=60.0,
    )

    assert context.remaining_time() == 45.0


def test_remaining_time_never_goes_negative():
    context = CombatContext(
        elapsed_time=75.0,
        fight_duration=60.0,
    )

    assert context.remaining_time() == 0.0


def test_remaining_time_is_unknown_without_fight_duration():
    context = CombatContext(
        elapsed_time=15.0,
    )

    assert context.remaining_time() is None    