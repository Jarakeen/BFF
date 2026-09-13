from __future__ import annotations

"""Proof-preserving class-route signature reduction for Extreme Health Recovery.

This service does not score recovery. It collapses legal class/subclass routes only
when they expose the same class-line and Class Mastery mechanics that the reviewed
Health Recovery passive frontier identified as potentially record-relevant.
Shared passives (race, armor, Assault, Emperor, Vampire, consumables) deliberately
remain outside the route signature because every class route can access them under
separate legality/runtime rules.
"""

from dataclasses import dataclass

from minmax.character_build.character_class import CharacterClass
from services.extreme_heal_class_route_service import ExtremeHealClassRoute


_RELEVANT_CLASS_LINES = frozenset(
    {
        "draconic_power",          # Elder Dragon
        "storm_calling",          # Capacitor
        "soldier_of_apocrypha",   # Wellspring of the Abyss
        "living_death",           # Undead Confederate
    }
)

_RELEVANT_CLASS_MASTERY = {
    CharacterClass.DRAGONKNIGHT: "booming_voice",
    CharacterClass.SORCERER: "sphere_of_influence",
    CharacterClass.TEMPLAR: "devout_guardian",
}


@dataclass(frozen=True)
class ExtremeHealthRecoveryClassRouteSignature:
    relevant_skill_lines: tuple[str, ...]
    class_mastery: str | None

    @property
    def identity(self) -> tuple[tuple[str, ...], str | None]:
        return self.relevant_skill_lines, self.class_mastery


@dataclass(frozen=True)
class ExtremeHealthRecoveryClassRouteSignatureGroup:
    signature: ExtremeHealthRecoveryClassRouteSignature
    representative: ExtremeHealClassRoute
    routes: tuple[ExtremeHealClassRoute, ...]


@dataclass(frozen=True)
class ExtremeHealthRecoveryClassRouteSignatureCatalog:
    source_route_count: int
    groups: tuple[ExtremeHealthRecoveryClassRouteSignatureGroup, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def projected_signature_count(self) -> int:
        return len(self.groups)

    @property
    def projection_complete(self) -> bool:
        return bool(
            self.source_route_count
            and self.groups
            and sum(len(group.routes) for group in self.groups) == self.source_route_count
            and not self.unresolved
        )


class ExtremeHealthRecoveryClassRouteSignatureService:
    """Collapse legal routes by reviewed Health Recovery class-mechanic identity."""

    @staticmethod
    def signature(route: ExtremeHealClassRoute) -> ExtremeHealthRecoveryClassRouteSignature:
        lines = tuple(
            sorted(
                set(route.equipped_skill_lines) & _RELEVANT_CLASS_LINES
            )
        )
        mastery = None
        if route.class_mastery_allowed:
            mastery = _RELEVANT_CLASS_MASTERY.get(route.base_class)
        return ExtremeHealthRecoveryClassRouteSignature(
            relevant_skill_lines=lines,
            class_mastery=mastery,
        )

    @staticmethod
    def _route_identity(route: ExtremeHealClassRoute) -> tuple[str, bool, tuple[str, ...]]:
        return (
            route.base_class.value,
            route.is_subclassed,
            tuple(route.equipped_skill_lines),
        )

    @classmethod
    def build(
        cls,
        routes: tuple[ExtremeHealClassRoute, ...],
    ) -> ExtremeHealthRecoveryClassRouteSignatureCatalog:
        buckets: dict[
            tuple[tuple[str, ...], str | None],
            list[ExtremeHealClassRoute],
        ] = {}
        unresolved: list[str] = []

        for route in routes:
            problems = tuple(route.configuration.validate(route.base_class))
            if problems:
                unresolved.append(
                    f"Illegal class route entered Health Recovery denominator: "
                    f"{cls._route_identity(route)!r}: {'; '.join(problems)}"
                )
                continue
            signature = cls.signature(route)
            buckets.setdefault(signature.identity, []).append(route)

        groups: list[ExtremeHealthRecoveryClassRouteSignatureGroup] = []
        for identity, members in buckets.items():
            ordered = tuple(sorted(members, key=cls._route_identity))
            signature = ExtremeHealthRecoveryClassRouteSignature(
                relevant_skill_lines=identity[0],
                class_mastery=identity[1],
            )
            groups.append(
                ExtremeHealthRecoveryClassRouteSignatureGroup(
                    signature=signature,
                    representative=ordered[0],
                    routes=ordered,
                )
            )

        groups.sort(
            key=lambda group: (
                group.signature.relevant_skill_lines,
                group.signature.class_mastery or "",
                cls._route_identity(group.representative),
            )
        )
        return ExtremeHealthRecoveryClassRouteSignatureCatalog(
            source_route_count=len(routes),
            groups=tuple(groups),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeHealthRecoveryClassRouteSignature",
    "ExtremeHealthRecoveryClassRouteSignatureCatalog",
    "ExtremeHealthRecoveryClassRouteSignatureGroup",
    "ExtremeHealthRecoveryClassRouteSignatureService",
]
