from __future__ import annotations

import pytest

from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_resource_class_route_dominance_projection_service import (
    ExtremeResourceClassRouteDominanceProjectionService,
)
from services.extreme_resource_class_route_projection_service import (
    ExtremeResourceClassRouteProjectionService,
)


class _Audit:
    def __init__(self, complete: bool):
        self.projection_complete = complete


class _AuditService:
    def __init__(self, complete: bool):
        self.complete = complete

    def build(self, _objective_key: str):
        return _Audit(self.complete)


def _service(*, complete: bool = True):
    exact = ExtremeResourceClassRouteProjectionService(
        passive_audit_service=_AuditService(complete),
    )
    return ExtremeResourceClassRouteDominanceProjectionService(
        route_projection_service=exact,
    )


@pytest.mark.parametrize("objective", ("max_magicka", "max_stamina"))
def test_complete_exact_projection_collapses_to_one_dominant_legal_route(objective):
    routes = ExtremeHealClassRouteService().all_routes()

    result = _service().build(objective, routes)

    assert result.projection_complete is True
    assert result.denominator_proven is True
    assert result.source_route_count == len(routes)
    assert result.projected_route_count == 8
    assert len(result.routes) == 1
    assert result.signature == (
        "daedric_summoning",
        "dark_magic",
        "siphoning",
    )
    witness = result.routes[0]
    assert witness.base_class.value == "sorcerer"
    assert witness.is_subclassed is True
    assert tuple(witness.equipped_skill_lines) == (
        "daedric_summoning",
        "dark_magic",
        "siphoning",
    )
    assert any("-> 8 exact signatures -> 1 dominant legal witness" in row for row in result.scope)


@pytest.mark.parametrize("objective", ("max_magicka", "max_stamina"))
def test_incomplete_exact_projection_fails_closed(objective):
    routes = ExtremeHealClassRouteService().all_routes()

    result = _service(complete=False).build(objective, routes)

    assert result.projection_complete is False
    assert result.denominator_proven is False
    assert result.routes == ()
    assert any("complete exact route-signature projection" in row for row in result.unresolved)


def test_dominance_projection_rejects_unreviewed_health_objective():
    with pytest.raises(KeyError, match="unreviewed Extreme class-route dominance objective"):
        _service().build("max_health", ExtremeHealClassRouteService().all_routes())
