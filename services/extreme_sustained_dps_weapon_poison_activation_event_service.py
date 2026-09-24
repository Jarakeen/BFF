from __future__ import annotations

"""Derive ZOS-proven weapon-poison activation opportunities for Objective #32.

Poison trigger eligibility intentionally reuses the reviewed weapon-attack damage
occurrence classifier used by weapon enchantments.  It then narrows opportunities
to the exact source bar carrying an equipped poison. Chance and the global poison
cooldown are owned by the sequence frontier, not by this service.
"""

from dataclasses import dataclass

from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    ExtremeSustainedDPSWeaponEnchantmentActivationEventService,
)


WEAPON_POISON_ACTIVATION_TRIGGER = "weapon_poison_activation"


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonActivationEventResult:
    events: tuple[RuntimeEvent, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponPoisonActivationEventService:
    """Resolve exact damaging events eligible to make a poison proc check."""

    def __init__(self, *, weapon_event_service: object) -> None:
        if weapon_event_service is None:
            raise ValueError(
                "weapon-poison activation events require weapon attack event service"
            )
        self.weapon_event_service = weapon_event_service

    @classmethod
    def from_database(cls, database_path):
        return cls(
            weapon_event_service=(
                ExtremeSustainedDPSWeaponEnchantmentActivationEventService.from_database(
                    database_path
                )
            )
        )

    @staticmethod
    def _poison_for_bar(build: PlayerBuild, source_bar: str | None) -> str:
        bar = str(source_bar or "").strip().casefold()
        if bar == "front":
            return str(getattr(build, "FrontBarPoison", "") or "").strip()
        if bar == "back":
            return str(getattr(build, "BackBarPoison", "") or "").strip()
        return ""

    def resolve(
        self,
        *,
        candidate,
        player_build: PlayerBuild,
        occurrence_provider: object,
        target_identity: str | None = None,
    ) -> ExtremeSustainedDPSWeaponPoisonActivationEventResult:
        base = self.weapon_event_service.resolve(
            candidate=candidate,
            occurrence_provider=occurrence_provider,
            target_identity=target_identity,
        )
        unresolved = list(tuple(getattr(base, "unresolved", ()) or ()))
        events: list[RuntimeEvent] = []
        equipped_bars = 0

        front = str(getattr(player_build, "FrontBarPoison", "") or "").strip()
        back = str(getattr(player_build, "BackBarPoison", "") or "").strip()
        equipped_bars += int(bool(front))
        equipped_bars += int(bool(back))

        for event in tuple(getattr(base, "events", ()) or ()):
            poison = self._poison_for_bar(player_build, event.source_bar)
            if not poison:
                continue
            if event.source_bar not in {"front", "back"}:
                unresolved.append(
                    f"{event.time_seconds:g}s #{event.sequence}: poison activation "
                    "requires exact front/back source-bar ownership"
                )
                continue
            events.append(
                RuntimeEvent(
                    time_seconds=float(event.time_seconds),
                    sequence=int(event.sequence),
                    trigger=WEAPON_POISON_ACTIVATION_TRIGGER,
                    source=event.source,
                    target=event.target,
                    source_bar=event.source_bar,
                )
            )

        ordered = tuple(
            sorted(
                events,
                key=lambda row: (
                    float(row.time_seconds),
                    int(row.sequence),
                    row.source.casefold(),
                ),
            )
        )
        return ExtremeSustainedDPSWeaponPoisonActivationEventResult(
            events=ordered,
            evidence=(
                *tuple(getattr(base, "evidence", ()) or ()),
                f"Weapon sets carrying poison: {equipped_bars}",
                f"Weapon-poison activation opportunities materialized: {len(ordered)}",
                "Poison opportunities are retained only when the exact source bar carries a poison.",
                "Chance and the global poison cooldown remain downstream sequence state.",
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "WEAPON_POISON_ACTIVATION_TRIGGER",
    "ExtremeSustainedDPSWeaponPoisonActivationEventResult",
    "ExtremeSustainedDPSWeaponPoisonActivationEventService",
]
