from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.character_class import CharacterClass
from services.extreme_global_search_universe_service import (
    ExtremeGlobalSearchUniverseService,
)


@dataclass(frozen=True)
class _Race:
    name: str


class _RaceRepository:
    def list_races(self):
        return [_Race("Warden Elf"), _Race("Argonian"), _Race("argonian"), _Race("")]


class _RouteService:
    def __init__(self, routes=()):
        self.routes = tuple(routes)

    def all_routes(self):
        return self.routes


def test_attribute_allocations_exhaust_the_64_point_integer_simplex():
    rows = ExtremeGlobalSearchUniverseService.attribute_allocations()

    # Number of non-negative integer solutions to h + m + s = 64:
    # C(66, 2) = 2145.
    assert len(rows) == 2145
    assert len({(row.health, row.magicka, row.stamina) for row in rows}) == 2145
    assert all(row.health + row.magicka + row.stamina == 64 for row in rows)
    assert all(min(row.health, row.magicka, row.stamina) >= 0 for row in rows)


def test_attribute_allocations_include_each_pure_resource_extreme():
    rows = ExtremeGlobalSearchUniverseService.attribute_allocations()
    triples = {(row.health, row.magicka, row.stamina) for row in rows}

    assert (64, 0, 0) in triples
    assert (0, 64, 0) in triples
    assert (0, 0, 64) in triples


def test_build_deduplicates_and_deterministically_orders_races():
    service = ExtremeGlobalSearchUniverseService(
        "unused.db",
        race_repository=_RaceRepository(),
        route_service=_RouteService((object(),)),
    )

    result = service.build()

    assert result.races == ("Argonian", "argonian", "Warden Elf")
    assert result.active_bars == ("front", "back")
    assert result.structural_denominator_proven is True


def test_empty_claimed_axis_prevents_structural_denominator_proof():
    service = ExtremeGlobalSearchUniverseService(
        "unused.db",
        race_repository=_RaceRepository(),
        route_service=_RouteService(()),
    )

    result = service.build()

    assert result.structural_denominator_proven is False


def test_real_route_service_covers_every_base_class_and_only_legal_routes(tmp_path):
    # Race enumeration is injected so this test exercises subclass legality
    # without needing an eso.db fixture.
    service = ExtremeGlobalSearchUniverseService(
        tmp_path / "unused.db",
        race_repository=_RaceRepository(),
    )

    result = service.build()

    assert {route.base_class for route in result.class_routes} == set(CharacterClass)
    assert result.class_routes
    assert all(not route.configuration.validate(route.base_class) for route in result.class_routes)


def test_dynamic_build_axes_remain_explicitly_deferred_not_silently_claimed():
    service = ExtremeGlobalSearchUniverseService(
        "unused.db",
        race_repository=_RaceRepository(),
        route_service=_RouteService((object(),)),
    )

    result = service.build()

    assert "gear and legal set/package topology" in result.deferred_dynamic_axes
    assert "potions" in result.deferred_dynamic_axes
    assert "skill-bar choices and morphs" in result.deferred_dynamic_axes
    assert "Champion Points" in result.deferred_dynamic_axes
    assert "runtime duration/uptime state for sustained objectives" in result.deferred_dynamic_axes
