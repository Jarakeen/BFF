from services.extreme_resource_equipment_trait_coverage_audit_service import (
    ExtremeResourceEquipmentTraitCoverageAuditService,
)


def test_current_trait_domains_are_fully_classified_for_max_resources():
    service = ExtremeResourceEquipmentTraitCoverageAuditService()

    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = service.build(objective)
        assert audit.denominator_proven is True
        assert audit.unresolved == ()
        assert set(audit.searched_armor_traits) == {"divines", "infused"}
        assert set(audit.searched_jewelry_traits) == {
            "arcane",
            "healthy",
            "protective",
            "robust",
            "triune",
        }
        assert set(audit.glyph_dependent_jewelry_traits) == {"infused"}


def test_jewelry_infused_keeps_projection_open_until_glyph_irrelevance_is_proven():
    audit = ExtremeResourceEquipmentTraitCoverageAuditService().build("max_health")

    assert audit.projection_complete(jewelry_glyph_irrelevance_proven=False) is False
    assert audit.projection_complete(jewelry_glyph_irrelevance_proven=True) is True


def test_unknown_future_trait_fails_closed(monkeypatch):
    import services.extreme_resource_equipment_trait_coverage_audit_service as module

    monkeypatch.setattr(module, "ARMOR_TRAITS", [*module.ARMOR_TRAITS, "Future Weirdness"])
    audit = module.ExtremeResourceEquipmentTraitCoverageAuditService().build("max_stamina")

    assert audit.denominator_proven is False
    assert any("future weirdness" in row for row in audit.unresolved)
