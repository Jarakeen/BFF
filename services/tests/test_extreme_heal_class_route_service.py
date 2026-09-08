from __future__ import annotations

from minmax.character_build.character_class import CLASS_SKILL_LINES, CharacterClass
from services.extreme_heal_class_route_service import (
    ExtremeHealClassRouteService,
    canonical_class_skill_line_id,
)


def test_skill_line_normalization_matches_canonical_class_ids() -> None:
    assert canonical_class_skill_line_id("Green Balance") == "green_balance"
    assert canonical_class_skill_line_id("Winter's Embrace") == "winters_embrace"
    assert canonical_class_skill_line_id("Restoring Light") == "restoring_light"


def test_routes_include_pure_class_and_legal_two_foreign_line_subclass() -> None:
    service = ExtremeHealClassRouteService()
    routes = service.routes_for_base_class(CharacterClass.WARDEN)

    pure = next(route for route in routes if not route.is_subclassed)
    assert set(pure.equipped_skill_lines) == set(CLASS_SKILL_LINES[CharacterClass.WARDEN])
    assert pure.foreign_skill_lines == ()
    assert pure.class_mastery_allowed is True

    subclass = next(
        route
        for route in routes
        if set(route.equipped_skill_lines)
        == {"green_balance", "restoring_light", "storm_calling"}
    )
    assert subclass.is_subclassed is True
    assert set(subclass.foreign_skill_lines) == {"restoring_light", "storm_calling"}
    assert subclass.class_mastery_allowed is False
    assert subclass.configuration.validate(CharacterClass.WARDEN) == ()


def test_routes_reject_two_foreign_lines_from_same_foreign_class() -> None:
    service = ExtremeHealClassRouteService()
    routes = service.routes_for_base_class(CharacterClass.WARDEN)

    forbidden = {"green_balance", "restoring_light", "aedric_spear"}
    assert not any(set(route.equipped_skill_lines) == forbidden for route in routes)


def test_skill_line_filter_finds_native_and_subclass_routes_deterministically() -> None:
    service = ExtremeHealClassRouteService()
    routes = service.routes_for_skill_line(
        "Restoring Light",
        base_class=CharacterClass.WARDEN,
    )

    assert routes
    assert all("restoring_light" in route.equipped_skill_lines for route in routes)
    assert all(route.base_class is CharacterClass.WARDEN for route in routes)
    assert all(route.is_subclassed for route in routes)
    assert routes == tuple(
        sorted(
            routes,
            key=lambda route: (
                route.is_subclassed,
                route.equipped_skill_lines,
            ),
        )
    )
