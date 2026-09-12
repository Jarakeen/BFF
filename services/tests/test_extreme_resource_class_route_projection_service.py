from __future__ import annotations

import pytest

from services.extreme_heal_class_route_service import ExtremeHealClassRouteService
from services.extreme_resource_class_route_projection_service import (
    ExtremeResourceClassRouteProjectionService,
)


class _Audit:
    def __init__(self, complete: bool):
        self.projection_complete = complete


class _AuditService:
    def __init__(self, complete: bool):
        self.complete = complete
        self.requested = []

    def build(self, objective_key: str):
        self.requested.append(objective_key)
        return _Audit(self.complete)


@pytest.mark.parametrize("objective", ("max_magicka", "max_stamina"))
def test_complete_passive_proof_collapses_routes_by_resource_class_line_signature(objective):
    routes = ExtremeHealClassRouteService().all_routes()
    audit = _AuditService(True)
    service = ExtremeResourceClassRouteProjectionService(
        passive_audit_service=audit,
    )

    result = service.build(objective, routes)

    assert result.projection_complete is True
    assert result.denominator_proven is True
    assert result.source_route_count == len(routes)
    assert len(result.routes) == len(result.signatures)
    assert len(result.routes) < len(routes)
    assert len(result.routes) <= 8
    assert result.relevant_class_lines == (
        "daedric_summoning",
        "dark_magic",
        "siphoning",
    )
    assert len(set(result.signatures)) == len(result.signatures)
    assert audit.requested == [objective]
    assert any("legal routes ->" in row for row in result.scope)


@pytest.mark.parametrize("objective", ("max_magicka", "max_stamina"))
def test_incomplete_passive_proof_prevents_route_projection(objective):
    routes = ExtremeHealClassRouteService().all_routes()
    result = ExtremeResourceClassRouteProjectionService(
        passive_audit_service=_AuditService(False),
    ).build(objective, routes)

    assert result.projection_complete is False
    assert result.denominator_proven is False
    assert any("complete canonical max-resource passive coverage" in row for row in result.unresolved)


def test_route_projection_rejects_unreviewed_objective():
    with pytest.raises(KeyError, match="unreviewed Extreme class-route projection objective"):
        ExtremeResourceClassRouteProjectionService(
            passive_audit_service=_AuditService(True),
        ).build("max_health", ExtremeHealClassRouteService().all_routes())
