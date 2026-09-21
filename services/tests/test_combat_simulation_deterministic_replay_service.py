from dataclasses import replace

from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationEvent,
    CombatSimulationResourceResult,
    CombatSimulationResult,
    CombatSimulationTargetState,
    SimulationEventPriority,
)
from services.combat_simulation_deterministic_replay_service import (
    CombatSimulationDeterministicReplayService,
)


def _result(**changes):
    base = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(),
        resources=(),
        effect_windows=(),
        target_state=None,
        unresolved=(),
    )
    return replace(base, **changes)


def test_replay_verifier_accepts_identical_deterministic_results() -> None:
    calls = []

    def runner():
        calls.append(True)
        return _result()

    verification = CombatSimulationDeterministicReplayService().verify(runner)

    assert len(calls) == 2
    assert verification.deterministic is True
    assert verification.differing_signature_fields == ()
    assert verification.first == verification.second


def test_replay_verifier_identifies_signature_field_drift() -> None:
    results = iter(
        (
            _result(),
            _result(unresolved=("runtime drift",), damage_unresolved=("damage drift",)),
        )
    )

    verification = CombatSimulationDeterministicReplayService().verify(
        lambda: next(results)
    )

    assert verification.deterministic is False
    assert verification.differing_signature_fields == (
        "unresolved",
        "damage_unresolved",
    )


def test_replay_verifier_requires_combat_simulation_result() -> None:
    try:
        CombatSimulationDeterministicReplayService().verify(lambda: object())
    except TypeError as exc:
        assert "CombatSimulationResult" in str(exc)
    else:
        raise AssertionError("Expected invalid replay result to fail closed")



def test_replay_verifier_reports_damage_unresolved_drift() -> None:
    results = iter(
        (
            _result(),
            _result(damage_unresolved=("damage drift",)),
        )
    )

    verification = CombatSimulationDeterministicReplayService().verify(
        lambda: next(results)
    )

    assert verification.deterministic is False
    assert verification.differing_signature_fields == ("damage_unresolved",)


def test_combat_simulation_result_rejects_non_finite_or_negative_duration() -> None:
    for value in (-1.0, float("nan"), float("inf"), float("-inf")):
        try:
            _result(duration_seconds=value)
        except ValueError as exc:
            assert "finite and non-negative" in str(exc)
        else:
            raise AssertionError("Expected invalid simulation result duration to fail closed")


def test_combat_simulation_result_rejects_event_beyond_duration() -> None:
    event = CombatSimulationEvent(
        time_seconds=6.0,
        priority=int(SimulationEventPriority.ACTION),
        sequence=0,
        event_type="action",
        source="Too Late",
    )

    try:
        _result(events=(event,))
    except ValueError as exc:
        assert "beyond its duration" in str(exc)
    else:
        raise AssertionError("Expected post-horizon result event to fail closed")


def test_combat_simulation_result_rejects_out_of_order_events() -> None:
    later = CombatSimulationEvent(
        time_seconds=2.0,
        priority=int(SimulationEventPriority.ACTION),
        sequence=0,
        event_type="action",
        source="Later",
    )
    earlier = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.ACTION),
        sequence=0,
        event_type="action",
        source="Earlier",
    )

    try:
        _result(events=(later, earlier))
    except ValueError as exc:
        assert "canonical timeline order" in str(exc)
    else:
        raise AssertionError("Expected out-of-order result events to fail closed")


def test_combat_simulation_result_rejects_invalid_bar_state() -> None:
    for field in ("initial_bar", "final_bar"):
        try:
            _result(**{field: "sideways"})
        except ValueError as exc:
            assert "front or back" in str(exc)
        else:
            raise AssertionError("Expected invalid combat result bar state to fail closed")


def test_combat_simulation_resource_result_rejects_invalid_summary_values() -> None:
    bad_cases = (
        dict(resource="", starting_amount=100, ending_amount=100, total_shortfall=0),
        dict(resource="magicka", starting_amount=-1, ending_amount=100, total_shortfall=0),
        dict(resource="magicka", starting_amount=100, ending_amount=-1, total_shortfall=0),
        dict(resource="magicka", starting_amount=100, ending_amount=100, total_shortfall=-1),
    )

    for kwargs in bad_cases:
        try:
            CombatSimulationResourceResult(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid combat resource summary to fail closed")


def test_combat_simulation_result_rejects_duplicate_resource_summaries() -> None:
    resource = CombatSimulationResourceResult(
        resource="magicka",
        starting_amount=30000,
        ending_amount=25000,
    )

    try:
        _result(resources=(resource, resource))
    except ValueError as exc:
        assert "resource identities must be unique" in str(exc)
    else:
        raise AssertionError("Expected duplicate resource summaries to fail closed")


def test_combat_simulation_result_rejects_orphan_resource_event() -> None:
    event = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.RESOURCE_COST),
        sequence=0,
        event_type="action_cost",
        source="Skill",
        payload=(
            ("resource", "stamina"),
            ("before", 20000),
            ("after", 18000),
        ),
    )
    summary = CombatSimulationResourceResult(
        resource="magicka",
        starting_amount=30000,
        ending_amount=30000,
    )

    try:
        _result(events=(event,), resources=(summary,))
    except ValueError as exc:
        assert "matching resource summaries" in str(exc)
    else:
        raise AssertionError("Expected orphan resource event to fail closed")


def test_combat_simulation_result_rejects_resource_event_without_identity() -> None:
    event = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.RESOURCE_COST),
        sequence=0,
        event_type="action_cost",
        source="Skill",
        payload=(("before", 20000), ("after", 18000)),
    )

    try:
        _result(events=(event,))
    except ValueError as exc:
        assert "require resource identity" in str(exc)
    else:
        raise AssertionError("Expected anonymous resource event to fail closed")


def test_combat_simulation_result_rejects_resource_summary_state_mismatch() -> None:
    event = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.RESOURCE_COST),
        sequence=0,
        event_type="action_cost",
        source="Skill",
        payload=(
            ("resource", "magicka"),
            ("before", 30000),
            ("after", 27000),
        ),
    )
    wrong_start = CombatSimulationResourceResult(
        resource="magicka",
        starting_amount=29000,
        ending_amount=27000,
    )
    wrong_end = CombatSimulationResourceResult(
        resource="magicka",
        starting_amount=30000,
        ending_amount=26000,
    )

    for summary, expected in (
        (wrong_start, "summary start does not match"),
        (wrong_end, "summary end does not match"),
    ):
        try:
            _result(events=(event,), resources=(summary,))
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(
                "Expected resource summary/event state mismatch to fail closed"
            )


def test_combat_simulation_result_rejects_health_change_without_target_state() -> None:
    event = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.HEALTH_CHANGE),
        sequence=0,
        event_type="health_change",
        source="Heal",
        payload=(
            ("recipient", "Tank 1"),
            ("before", 20000),
            ("after", 22000),
        ),
    )

    try:
        _result(events=(event,))
    except ValueError as exc:
        assert "health changes require target state" in str(exc)
    else:
        raise AssertionError("Expected Health change without target state to fail closed")


def test_combat_simulation_result_rejects_unknown_health_change_recipient() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Tank 1",
                "ally",
                current_health=20000,
                maximum_health=25000,
            ),
        )
    )
    event = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.HEALTH_CHANGE),
        sequence=0,
        event_type="health_change",
        source="Heal",
        payload=(
            ("recipient", "Tank 2"),
            ("before", 20000),
            ("after", 22000),
        ),
    )

    try:
        _result(events=(event,), target_state=state)
    except ValueError as exc:
        assert "not present in target state" in str(exc)
    else:
        raise AssertionError("Expected unknown Health recipient to fail closed")


def test_combat_simulation_result_rejects_broken_health_change_chain() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Tank 1",
                "ally",
                current_health=20000,
                maximum_health=25000,
            ),
        )
    )
    first = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.HEALTH_CHANGE),
        sequence=0,
        event_type="health_change",
        source="First",
        payload=(
            ("recipient", "Tank 1"),
            ("before", 20000),
            ("after", 22000),
            ("maximum_health", 25000),
        ),
    )
    second = CombatSimulationEvent(
        time_seconds=2.0,
        priority=int(SimulationEventPriority.HEALTH_CHANGE),
        sequence=0,
        event_type="health_change",
        source="Second",
        payload=(
            ("recipient", "Tank 1"),
            ("before", 21000),
            ("after", 23000),
            ("maximum_health", 25000),
        ),
    )

    try:
        _result(events=(first, second), target_state=state)
    except ValueError as exc:
        assert "before/after chain is inconsistent" in str(exc)
    else:
        raise AssertionError("Expected broken Health chain to fail closed")


def test_combat_simulation_result_rejects_death_without_zero_health() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=5000,
                maximum_health=10000,
            ),
        )
    )
    death = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.EXPIRATION),
        sequence=0,
        event_type="death",
        source="Execute",
        payload=(
            ("recipient", "Boss"),
            ("origin_event_type", "outgoing_damage"),
        ),
    )

    try:
        _result(events=(death,), target_state=state)
    except ValueError as exc:
        assert "requires zero Health state" in str(exc)
    else:
        raise AssertionError("Expected unsupported death evidence to fail closed")


def test_combat_simulation_result_accepts_death_after_lethal_health_change() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=5000,
                maximum_health=10000,
            ),
        )
    )
    health = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.HEALTH_CHANGE),
        sequence=0,
        event_type="health_change",
        source="Execute",
        payload=(
            ("recipient", "Boss"),
            ("before", 5000),
            ("after", 0),
            ("maximum_health", 10000),
            ("origin_event_type", "outgoing_damage"),
        ),
    )
    death = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.EXPIRATION),
        sequence=0,
        event_type="death",
        source="Execute",
        payload=(
            ("recipient", "Boss"),
            ("origin_event_type", "outgoing_damage"),
        ),
    )

    result = _result(events=(health, death), target_state=state)

    assert result.events == (health, death)


def test_combat_simulation_result_rejects_death_before_later_lethal_health_change() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=5000,
                maximum_health=10000,
            ),
        )
    )
    death = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.EXPIRATION),
        sequence=0,
        event_type="death",
        source="Too Early",
        payload=(("recipient", "Boss"),),
    )
    health = CombatSimulationEvent(
        time_seconds=2.0,
        priority=int(SimulationEventPriority.HEALTH_CHANGE),
        sequence=0,
        event_type="health_change",
        source="Later Execute",
        payload=(
            ("recipient", "Boss"),
            ("before", 5000),
            ("after", 0),
            ("maximum_health", 10000),
        ),
    )

    try:
        _result(events=(death, health), target_state=state)
    except ValueError as exc:
        assert "requires zero Health state" in str(exc)
    else:
        raise AssertionError("Expected premature death event to fail closed")


def test_combat_simulation_result_rejects_invalid_health_event_arithmetic() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Tank 1",
                "ally",
                current_health=20000,
                maximum_health=25000,
            ),
        )
    )
    bad_damage = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.HEALTH_CHANGE),
        sequence=0,
        event_type="health_change",
        source="Bad Damage",
        payload=(
            ("recipient", "Tank 1"),
            ("before", 20000),
            ("applied_damage", 3000.0),
            ("after", 18000),
            ("maximum_health", 25000),
        ),
    )
    bad_heal = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.HEALTH_CHANGE),
        sequence=0,
        event_type="health_change",
        source="Bad Heal",
        payload=(
            ("recipient", "Tank 1"),
            ("before", 20000),
            ("applied_heal", 2000.0),
            ("after", 23000),
            ("maximum_health", 25000),
        ),
    )

    for event, expected in (
        (bad_damage, "damage Health arithmetic is inconsistent"),
        (bad_heal, "healing Health arithmetic is inconsistent"),
    ):
        try:
            _result(events=(event,), target_state=state)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("Expected invalid Health arithmetic to fail closed")


def test_combat_simulation_result_rejects_health_change_without_known_maximum() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Tank 1",
                "ally",
                current_health=20000,
                maximum_health=None,
            ),
        )
    )
    event = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.HEALTH_CHANGE),
        sequence=0,
        event_type="health_change",
        source="Heal",
        payload=(
            ("recipient", "Tank 1"),
            ("before", 20000),
            ("after", 22000),
        ),
    )

    try:
        _result(events=(event,), target_state=state)
    except ValueError as exc:
        assert "requires known maximum Health" in str(exc)
    else:
        raise AssertionError("Expected Health change without maximum Health to fail closed")


def test_combat_simulation_result_rejects_effect_window_start_beyond_duration() -> None:
    from minmax.runtime_effect_window import RuntimeEffectActiveWindow

    window = RuntimeEffectActiveWindow(
        effect_name="future_effect",
        source="Skill",
        start_time_seconds=6.0,
        end_time_seconds=10.0,
    )

    try:
        _result(effect_windows=(window,))
    except ValueError as exc:
        assert "cannot start beyond result duration" in str(exc)
    else:
        raise AssertionError("Expected future effect window to fail closed")


def test_combat_simulation_result_rejects_out_of_order_effect_windows() -> None:
    from minmax.runtime_effect_window import RuntimeEffectActiveWindow

    later = RuntimeEffectActiveWindow(
        effect_name="later",
        source="Skill",
        start_time_seconds=2.0,
        end_time_seconds=4.0,
    )
    earlier = RuntimeEffectActiveWindow(
        effect_name="earlier",
        source="Skill",
        start_time_seconds=1.0,
        end_time_seconds=3.0,
    )

    try:
        _result(effect_windows=(later, earlier))
    except ValueError as exc:
        assert "effect windows must be in canonical timeline order" in str(exc)
    else:
        raise AssertionError("Expected out-of-order effect windows to fail closed")


def test_combat_simulation_result_rejects_final_bar_mismatch() -> None:
    swap = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.ACTION),
        sequence=0,
        event_type="action",
        source="bar_swap",
        payload=(
            ("kind", "bar_swap"),
            ("bar", "back"),
        ),
    )

    try:
        _result(events=(swap,), final_bar="front")
    except ValueError as exc:
        assert "final bar does not match event state" in str(exc)
    else:
        raise AssertionError("Expected final bar/event mismatch to fail closed")


def test_combat_simulation_result_rejects_invalid_bar_swap_destination() -> None:
    swap = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.ACTION),
        sequence=0,
        event_type="action",
        source="bar_swap",
        payload=(
            ("kind", "bar_swap"),
            ("bar", "sideways"),
        ),
    )

    try:
        _result(events=(swap,))
    except ValueError as exc:
        assert "bar swap requires front or back destination" in str(exc)
    else:
        raise AssertionError("Expected invalid bar swap destination to fail closed")


def test_combat_simulation_result_rejects_duplicate_effect_windows() -> None:
    from minmax.runtime_effect_window import RuntimeEffectActiveWindow

    window = RuntimeEffectActiveWindow(
        effect_name="major_slayer",
        source="Skill",
        start_time_seconds=1.0,
        end_time_seconds=5.0,
        target="group",
        sequence=0,
        magnitude=10.0,
    )

    try:
        _result(effect_windows=(window, window))
    except ValueError as exc:
        assert "effect window identities must be unique" in str(exc)
    else:
        raise AssertionError("Expected duplicate effect windows to fail closed")
