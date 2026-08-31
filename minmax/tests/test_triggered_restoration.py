from minmax.resource_costs import ResourceType
from minmax.triggered_restoration import (
    RESTORATION_STAFF_ABSORB,
    RESTORATION_STAFF_ABSORB_COOLDOWN_SECONDS,
    WARDEN_NATURES_GIFT,
    WARDEN_NATURES_GIFT_COOLDOWN_SECONDS,
)


def test_restoration_staff_absorb_creates_600_magicka_restore_event() -> None:
    events = RESTORATION_STAFF_ABSORB.create_events(time_seconds=3.5)

    assert RESTORATION_STAFF_ABSORB.cooldown_seconds == RESTORATION_STAFF_ABSORB_COOLDOWN_SECONDS == 0.25
    assert len(events) == 1
    event = events[0]
    assert event.time_seconds == 3.5
    assert event.resource is ResourceType.MAGICKA
    assert event.amount == 600
    assert event.source == "Restoration Staff: Absorb"


def test_warden_natures_gift_creates_magicka_and_stamina_events() -> None:
    events = WARDEN_NATURES_GIFT.create_events(time_seconds=7.0)

    assert WARDEN_NATURES_GIFT.cooldown_seconds == WARDEN_NATURES_GIFT_COOLDOWN_SECONDS == 1.0
    assert [(event.resource, event.amount) for event in events] == [
        (ResourceType.MAGICKA, 250),
        (ResourceType.STAMINA, 250),
    ]
    assert all(event.time_seconds == 7.0 for event in events)
    assert all(event.source == "Warden: Nature's Gift" for event in events)
