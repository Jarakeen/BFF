from __future__ import annotations

"""Enumerate objective-neutral legal character axes for Extreme global search.

This service owns *structural* enumeration only.  It deliberately does not score
ESO mechanics or decide which race, class route, gear set, skill, food, potion,
or runtime state is best for an objective.  Those decisions belong to canonical
mechanics + objective evaluators.

The universe is useful to Extreme Records because it gives denominator proof a
stable starting point.  Comp Maker may consume resulting records, but should not
re-enumerate this legality space itself.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import AttributeAllocation
from minmax.race_repository import RaceRepository
from services.extreme_heal_class_route_service import (
    ExtremeHealClassRoute,
    ExtremeHealClassRouteService,
)


@dataclass(frozen=True)
class ExtremeGlobalSearchUniverse:
    races: tuple[str, ...]
    class_routes: tuple[ExtremeHealClassRoute, ...]
    attribute_allocations: tuple[AttributeAllocation, ...]
    active_bars: tuple[str, ...]
    structural_scope: tuple[str, ...]
    deferred_dynamic_axes: tuple[str, ...]

    @property
    def structural_denominator_proven(self) -> bool:
        """Whether every axis this service claims to own was exhaustively enumerated."""
        return bool(
            self.races
            and self.class_routes
            and self.attribute_allocations
            and self.active_bars == ("front", "back")
        )


class ExtremeGlobalSearchUniverseService:
    """Build the reusable finite legality universe shared by Extreme objectives."""

    ATTRIBUTE_POINTS = 64
    ACTIVE_BARS = ("front", "back")

    STRUCTURAL_SCOPE = (
        "all canonical playable races present in eso.db",
        "all structurally legal ESO base-class / three-class-line routes",
        "all 64-point Health/Magicka/Stamina attribute allocations",
        "front and back active-bar contexts",
    )

    # These are deliberately not called omissions.  They are dynamic scoring axes
    # that later exhaustive-search layers must enumerate against this structural
    # universe before an Extreme Record may prove its global denominator.
    DEFERRED_DYNAMIC_AXES = (
        "gear and legal set/package topology",
        "armor, jewelry, and weapon traits",
        "glyphs/enchants",
        "Mundus",
        "food/drink",
        "potions",
        "skill-bar choices and morphs",
        "Champion Points",
        "class/skill/armor/weapon/guild passive ranks",
        "legal self-provided named buffs and proc states",
        "recipient/target state for conditional objectives",
        "runtime duration/uptime state for sustained objectives",
    )

    def __init__(
        self,
        database_path: str | Path,
        *,
        race_repository: RaceRepository | None = None,
        route_service: ExtremeHealClassRouteService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.race_repository = race_repository or RaceRepository(self.database_path)
        self.route_service = route_service or ExtremeHealClassRouteService()

    def build(self) -> ExtremeGlobalSearchUniverse:
        races = tuple(
            sorted(
                {
                    str(race.name).strip()
                    for race in self.race_repository.list_races()
                    if str(race.name).strip()
                },
                key=str.casefold,
            )
        )
        routes = tuple(self.route_service.all_routes())
        allocations = self.attribute_allocations()
        return ExtremeGlobalSearchUniverse(
            races=races,
            class_routes=routes,
            attribute_allocations=allocations,
            active_bars=self.ACTIVE_BARS,
            structural_scope=self.STRUCTURAL_SCOPE,
            deferred_dynamic_axes=self.DEFERRED_DYNAMIC_AXES,
        )

    @classmethod
    def attribute_allocations(cls) -> tuple[AttributeAllocation, ...]:
        """Enumerate the complete integer simplex for ESO's 64 attribute points."""
        rows: list[AttributeAllocation] = []
        total = int(cls.ATTRIBUTE_POINTS)
        for health in range(total + 1):
            for magicka in range(total - health + 1):
                stamina = total - health - magicka
                rows.append(
                    AttributeAllocation(
                        health=health,
                        magicka=magicka,
                        stamina=stamina,
                    )
                )
        return tuple(rows)
