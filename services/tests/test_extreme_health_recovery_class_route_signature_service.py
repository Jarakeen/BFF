from minmax.character_build.character_class import CharacterClass
from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_health_recovery_class_route_signature_service import (
    ExtremeHealthRecoveryClassRouteSignatureService,
)


def test_all_legal_routes_are_partitioned_by_health_recovery_signature():
    routes = ExtremeHealClassRouteService().all_routes()
    result = ExtremeHealthRecoveryClassRouteSignatureService.build(routes)

    assert result.source_route_count == len(routes)
    assert result.projection_complete
    assert sum(len(group.routes) for group in result.groups) == len(routes)
    assert result.projected_signature_count < len(routes)


def test_pure_sorcerer_signature_preserves_storm_calling_and_mastery():
    routes = ExtremeHealClassRouteService().routes_for_base_class(CharacterClass.SORCERER)
    pure = next(route for route in routes if not route.is_subclassed)

    signature = ExtremeHealthRecoveryClassRouteSignatureService.signature(pure)

    assert "storm_calling" in signature.relevant_skill_lines
    assert signature.class_mastery == "sphere_of_influence"


def test_subclassed_sorcerer_route_does_not_claim_class_mastery():
    routes = ExtremeHealClassRouteService().routes_for_base_class(CharacterClass.SORCERER)
    subclassed = next(route for route in routes if route.is_subclassed)

    signature = ExtremeHealthRecoveryClassRouteSignatureService.signature(subclassed)

    assert signature.class_mastery is None
