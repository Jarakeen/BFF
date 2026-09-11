from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from services.extreme_jewelry_resource_glyph_relevance_service import (
    ExtremeJewelryResourceGlyphRelevanceService,
)


class _Repository:
    def list_names(self):
        return (
            "Glyph of Health Recovery",
            "Glyph of Magicka Recovery",
            "Glyph of Stamina Recovery",
            "Glyph of Increase Magical Harm",
            "Glyph of Increase Physical Harm",
        )

    def get_jewelry_glyph_effect_by_name(self, name, *, use_max_value=True):
        effects = {
            "Glyph of Health Recovery": (
                Effect(EffectOperation.ADD, 100.0, name, stat=StatId.HEALTH_RECOVERY),
            ),
            "Glyph of Magicka Recovery": (
                Effect(EffectOperation.ADD, 100.0, name, stat=StatId.MAGICKA_RECOVERY),
            ),
            "Glyph of Stamina Recovery": (
                Effect(EffectOperation.ADD, 100.0, name, stat=StatId.STAMINA_RECOVERY),
            ),
            "Glyph of Increase Magical Harm": (
                Effect(EffectOperation.ADD, 100.0, name, stat=StatId.SPELL_DAMAGE),
            ),
            "Glyph of Increase Physical Harm": (
                Effect(EffectOperation.ADD, 100.0, name, stat=StatId.WEAPON_DAMAGE),
            ),
        }
        return list(effects.get(name, ()))


class _RelevantRepository(_Repository):
    def list_names(self):
        return (*super().list_names(), "Glyph of Impossible Health")

    def get_jewelry_glyph_effect_by_name(self, name, *, use_max_value=True):
        if name == "Glyph of Impossible Health":
            return [Effect(EffectOperation.ADD, 500.0, name, stat=StatId.MAX_HEALTH)]
        return super().get_jewelry_glyph_effect_by_name(name, use_max_value=use_max_value)


class _EmptyEffectRepository(_Repository):
    def list_names(self):
        return (*super().list_names(), "Glyph of Mystery")


class _StatlessRepository(_Repository):
    def list_names(self):
        return (*super().list_names(), "Glyph of Mystery")

    def get_jewelry_glyph_effect_by_name(self, name, *, use_max_value=True):
        if name == "Glyph of Mystery":
            return [Effect(EffectOperation.ADD, 10.0, name, stat=None)]
        return super().get_jewelry_glyph_effect_by_name(name, use_max_value=use_max_value)


def test_reviewed_catalog_proves_resource_irrelevance_when_no_glyph_targets_resource():
    service = ExtremeJewelryResourceGlyphRelevanceService(repository=_Repository())

    for objective in ("max_health", "max_magicka", "max_stamina"):
        audit = service.build(objective)
        assert audit.glyphs_reviewed == 5
        assert audit.relevant_glyphs == ()
        assert audit.denominator_proven
        assert audit.objective_irrelevance_proven
        assert audit.unresolved == ()


def test_resource_relevant_glyph_blocks_irrelevance_but_not_denominator_proof():
    audit = ExtremeJewelryResourceGlyphRelevanceService(repository=_RelevantRepository()).build(
        "max_health"
    )

    assert audit.denominator_proven
    assert not audit.objective_irrelevance_proven
    assert audit.relevant_glyphs == ("Glyph of Impossible Health",)


def test_missing_mapped_effects_fail_closed():
    audit = ExtremeJewelryResourceGlyphRelevanceService(repository=_EmptyEffectRepository()).build(
        "max_health"
    )

    assert not audit.denominator_proven
    assert not audit.objective_irrelevance_proven
    assert any("Glyph of Mystery" in row for row in audit.unresolved)


def test_statless_effects_fail_closed():
    audit = ExtremeJewelryResourceGlyphRelevanceService(repository=_StatlessRepository()).build(
        "max_health"
    )

    assert not audit.denominator_proven
    assert any("stat identity" in row for row in audit.unresolved)


def test_empty_catalog_and_unreviewed_objective_fail_closed():
    class _EmptyRepository:
        def list_names(self):
            return ()

        def get_jewelry_glyph_effect_by_name(self, name, *, use_max_value=True):
            return ()

    audit = ExtremeJewelryResourceGlyphRelevanceService(repository=_EmptyRepository()).build(
        "max_health"
    )
    assert not audit.denominator_proven
    assert any("catalog is empty" in row for row in audit.unresolved)

    try:
        ExtremeJewelryResourceGlyphRelevanceService(repository=_Repository()).build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme jewelry resource glyph objective" in str(exc)
    else:
        raise AssertionError("expected unreviewed objective to fail closed")
