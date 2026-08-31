import pytest

from minmax.resource_costs import ResourceType
from minmax.resource_state import StaticResourcePool
from minmax.restoration_events import (
    ResourceRestorationEvent,
    apply_resource_restoration_event,
)


def _pool(resource: ResourceType, maximum: int = 30000) -> StaticResourcePool:
    return StaticResourcePool(
        resource=resource,
        maximum=maximum,
        displayed_recovery=0,
    )


def test_flat_restoration_event_applies_full_amount() -> None:
    event = ResourceRestorationEvent(
        time_seconds=3.5,
        resource=ResourceType.MAGICKA,
        amount=1680,
        source="Test flat restore",
    )

    result = apply_resource_restoration_event(
        _pool(ResourceType.MAGICKA),
        current_amount=20000,
        event=event,
    )

    assert result.previous_amount == 20000
    assert result.attempted_restore == 1680
    assert result.applied_restore == 1680
    assert result.resulting_amount == 21680
    assert result.wasted_restore == 0


def test_flat_restoration_clamps_at_pool_maximum_and_records_waste() -> None:
    event = ResourceRestorationEvent(
        time_seconds=1.0,
        resource=ResourceType.STAMINA,
        amount=2500,
        source="Test stamina restore",
    )

    result = apply_resource_restoration_event(
        _pool(ResourceType.STAMINA, maximum=30000),
        current_amount=29000,
        event=event,
    )

    assert result.applied_restore == 1000
    assert result.resulting_amount == 30000
    assert result.wasted_restore == 1500


def test_zero_amount_restoration_event_is_valid_and_noop() -> None:
    event = ResourceRestorationEvent(
        time_seconds=0.0,
        resource=ResourceType.HEALTH,
        amount=0,
        source="Zero restore",
    )

    result = apply_resource_restoration_event(
        _pool(ResourceType.HEALTH),
        current_amount=12000,
        event=event,
    )

    assert result.applied_restore == 0
    assert result.resulting_amount == 12000
    assert result.wasted_restore == 0


def test_restoration_event_rejects_resource_mismatch() -> None:
    event = ResourceRestorationEvent(
        time_seconds=2.0,
        resource=ResourceType.MAGICKA,
        amount=1000,
        source="Wrong resource",
    )

    with pytest.raises(ValueError, match="does not match pool"):
        apply_resource_restoration_event(
            _pool(ResourceType.STAMINA),
            current_amount=10000,
            event=event,
        )


def test_restoration_event_rejects_invalid_identity_or_state() -> None:
    with pytest.raises(ValueError, match="time cannot be negative"):
        ResourceRestorationEvent(
            time_seconds=-0.1,
            resource=ResourceType.MAGICKA,
            amount=100,
            source="Bad time",
        )

    with pytest.raises(ValueError, match="amount cannot be negative"):
        ResourceRestorationEvent(
            time_seconds=0.0,
            resource=ResourceType.MAGICKA,
            amount=-1,
            source="Bad amount",
        )

    with pytest.raises(ValueError, match="requires a source"):
        ResourceRestorationEvent(
            time_seconds=0.0,
            resource=ResourceType.MAGICKA,
            amount=100,
            source="",
        )

    event = ResourceRestorationEvent(
        time_seconds=0.0,
        resource=ResourceType.MAGICKA,
        amount=100,
        source="Valid",
    )
    with pytest.raises(ValueError, match="must be between"):
        apply_resource_restoration_event(
            _pool(ResourceType.MAGICKA),
            current_amount=30001,
            event=event,
        )
