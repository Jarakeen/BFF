from models.combat_simulation import CombatSimulationEvent, SimulationEventPriority
from services.combat_simulation_event_queue import CombatSimulationEventQueue


def _event(*, payload, source="Same Source"):
    return CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=0,
        event_type="incoming_damage",
        source=source,
        payload=payload,
    )


def test_event_queue_does_not_compare_payload_values() -> None:
    queue = CombatSimulationEventQueue()
    first = _event(payload=(("value", 1),))
    second = _event(payload=(("value", {"nested": "mapping"}),))

    queue.push(first)
    queue.push(second)

    assert queue.pop() is first
    assert queue.pop() is second


def test_event_queue_uses_semantic_coordinates_before_insertion_order() -> None:
    queue = CombatSimulationEventQueue()
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

    queue.push(later)
    queue.push(earlier)

    assert queue.pop() is earlier
    assert queue.pop() is later


def test_equal_semantic_event_keys_preserve_deterministic_insertion_order() -> None:
    queue = CombatSimulationEventQueue()
    first = _event(payload=(("marker", "first"),))
    second = _event(payload=(("marker", "second"),))

    queue.extend((first, second))

    assert [queue.pop(), queue.pop()] == [first, second]
