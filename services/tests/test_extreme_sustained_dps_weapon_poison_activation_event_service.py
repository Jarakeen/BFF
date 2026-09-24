from types import SimpleNamespace

from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_weapon_poison_activation_event_service import (
    ExtremeSustainedDPSWeaponPoisonActivationEventService,
    WEAPON_POISON_ACTIVATION_TRIGGER,
)


class _WeaponEvents:
    def resolve(self, **_kwargs):
        return SimpleNamespace(
            events=(
                RuntimeEvent(
                    time_seconds=1.0,
                    sequence=0,
                    trigger="weapon_enchantment_activation",
                    source="Front Light Attack",
                    target="Boss",
                    source_bar="front",
                ),
                RuntimeEvent(
                    time_seconds=2.0,
                    sequence=1,
                    trigger="weapon_enchantment_activation",
                    source="Back Light Attack",
                    target="Boss",
                    source_bar="back",
                ),
            ),
            evidence=("reviewed weapon damage opportunities",),
            unresolved=(),
        )


def test_poison_activation_keeps_only_source_bars_with_poison() -> None:
    service = ExtremeSustainedDPSWeaponPoisonActivationEventService(
        weapon_event_service=_WeaponEvents()
    )
    build = PlayerBuild(FrontBarPoison="Damage Health Poison IX")

    result = service.resolve(
        candidate=object(),
        player_build=build,
        occurrence_provider=object(),
        target_identity="Boss",
    )

    assert result.resolved is True
    assert len(result.events) == 1
    event = result.events[0]
    assert event.time_seconds == 1.0
    assert event.source_bar == "front"
    assert event.trigger == WEAPON_POISON_ACTIVATION_TRIGGER


def test_poison_activation_preserves_both_poisoned_bars() -> None:
    service = ExtremeSustainedDPSWeaponPoisonActivationEventService(
        weapon_event_service=_WeaponEvents()
    )
    build = PlayerBuild(
        FrontBarPoison="Front Poison",
        BackBarPoison="Back Poison",
    )

    result = service.resolve(
        candidate=object(),
        player_build=build,
        occurrence_provider=object(),
    )

    assert [event.source_bar for event in result.events] == ["front", "back"]
    assert any("Weapon sets carrying poison: 2" in row for row in result.evidence)
