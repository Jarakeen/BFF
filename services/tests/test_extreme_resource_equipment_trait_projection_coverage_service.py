from types import SimpleNamespace

import services.extreme_resource_equipment_trait_projection_coverage_service as module
from services.extreme_resource_equipment_trait_projection_coverage_service import (
    ExtremeResourceEquipmentTraitProjectionCoverageService,
)


class _Builder:
    def __init__(self, value):
        self.value = value

    def build(self, key):
        assert key == "max_health"
        return self.value


def test_projection_closes_only_when_all_equipment_trait_evidence_is_complete(monkeypatch):
    monkeypatch.setattr(
        module,
        "ExtremeResourceEquipmentTraitCoverageAuditService",
        lambda: _Builder(
            SimpleNamespace(
                unresolved=(),
                projection_complete=lambda **kwargs: kwargs["jewelry_glyph_irrelevance_proven"],
            )
        ),
    )
    monkeypatch.setattr(
        module,
        "ExtremeJewelryResourceStaticTraitStateService",
        lambda path: _Builder(
            SimpleNamespace(denominator_proven=True, states=(object(),), unresolved=())
        ),
    )
    monkeypatch.setattr(
        module,
        "ExtremeJewelryResourceGlyphRelevanceService",
        lambda path: _Builder(
            SimpleNamespace(
                denominator_proven=True,
                objective_irrelevance_proven=True,
                unresolved=(),
            )
        ),
    )
    monkeypatch.setattr(
        module,
        "ExtremeWeaponResourceRelevanceService",
        lambda path: _Builder(
            SimpleNamespace(
                denominator_proven=True,
                objective_irrelevance_proven=True,
                unresolved=(),
            )
        ),
    )

    result = ExtremeResourceEquipmentTraitProjectionCoverageService("fake.db").build(
        "max_health"
    )

    assert result.projection_complete is True
    assert result.unresolved == ()


def test_projection_fails_closed_when_jewelry_glyph_irrelevance_is_not_proven(monkeypatch):
    monkeypatch.setattr(
        module,
        "ExtremeResourceEquipmentTraitCoverageAuditService",
        lambda: _Builder(
            SimpleNamespace(
                unresolved=(),
                projection_complete=lambda **kwargs: kwargs["jewelry_glyph_irrelevance_proven"],
            )
        ),
    )
    monkeypatch.setattr(
        module,
        "ExtremeJewelryResourceStaticTraitStateService",
        lambda path: _Builder(
            SimpleNamespace(denominator_proven=True, states=(object(),), unresolved=())
        ),
    )
    monkeypatch.setattr(
        module,
        "ExtremeJewelryResourceGlyphRelevanceService",
        lambda path: _Builder(
            SimpleNamespace(
                denominator_proven=True,
                objective_irrelevance_proven=False,
                unresolved=("glyph relevance unresolved",),
            )
        ),
    )
    monkeypatch.setattr(
        module,
        "ExtremeWeaponResourceRelevanceService",
        lambda path: _Builder(
            SimpleNamespace(
                denominator_proven=True,
                objective_irrelevance_proven=True,
                unresolved=(),
            )
        ),
    )

    result = ExtremeResourceEquipmentTraitProjectionCoverageService("fake.db").build(
        "max_health"
    )

    assert result.projection_complete is False
    assert result.unresolved == ("glyph relevance unresolved",)
