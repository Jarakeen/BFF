import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind
from tools.audit_phase13_saved_build_recovery_heavy_rotation import (
    build_verified_heavy_restore_resolver,
)


def _heavy(*, time_seconds: float = 2.0, bar: str = "front") -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.HEAVY_ATTACK,
        name="Heavy Attack",
        bar=bar,
    )


def test_audit_restore_resolver_places_restore_at_heavy_completion() -> None:
    resolver = build_verified_heavy_restore_resolver(
        amount=4200,
        channel_seconds=1.8,
        bar="front",
    )

    event = resolver(_heavy(time_seconds=2.0, bar="front"))

    assert event is not None
    assert event.time_seconds == pytest.approx(3.8)
    assert event.resource is ResourceType.MAGICKA
    assert event.amount == 4200
    assert "caller-supplied" in event.source.casefold()


def test_audit_restore_resolver_ignores_heavies_on_other_bar() -> None:
    resolver = build_verified_heavy_restore_resolver(
        amount=4200,
        channel_seconds=1.8,
        bar="front",
    )

    assert resolver(_heavy(bar="back")) is None


def test_audit_restore_resolver_ignores_non_heavy_actions() -> None:
    resolver = build_verified_heavy_restore_resolver(
        amount=4200,
        channel_seconds=1.8,
    )
    action = RotationAction(
        time_seconds=2.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Combat Prayer",
        bar="front",
    )

    assert resolver(action) is None


def test_audit_restore_resolver_rejects_invalid_evidence() -> None:
    with pytest.raises(ValueError, match="restore amount"):
        build_verified_heavy_restore_resolver(amount=0, channel_seconds=1.8)

    with pytest.raises(ValueError, match="channel"):
        build_verified_heavy_restore_resolver(amount=4200, channel_seconds=0)

    with pytest.raises(ValueError, match="restore bar"):
        build_verified_heavy_restore_resolver(
            amount=4200,
            channel_seconds=1.8,
            bar="middle",
        )
