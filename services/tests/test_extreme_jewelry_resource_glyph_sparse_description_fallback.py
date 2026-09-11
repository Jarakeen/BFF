from services.extreme_jewelry_resource_glyph_relevance_service import (
    ExtremeJewelryResourceGlyphRelevanceService,
)


class _Repository:
    def __init__(self, description):
        self.description = description

    def list_names(self):
        return ("Glyph of Flame Resist",)

    def get_jewelry_glyph_effect_types_by_name(self, name):
        assert name == "Glyph of Flame Resist"
        return ()

    def get_jewelry_glyph_descriptions_by_name(self, name):
        assert name == "Glyph of Flame Resist"
        return (self.description,)


def test_sparse_flame_resistance_description_is_proven_irrelevant_to_max_health():
    audit = ExtremeJewelryResourceGlyphRelevanceService(
        repository=_Repository("Adds 1800 Flame Resistance."),
    ).build("max_health")

    assert audit.denominator_proven is True
    assert audit.objective_irrelevance_proven is True
    assert audit.relevant_glyphs == ()
    assert audit.irrelevant_glyphs == ("Glyph of Flame Resist",)
    assert audit.unresolved == ()


def test_sparse_direct_max_health_description_remains_relevant():
    audit = ExtremeJewelryResourceGlyphRelevanceService(
        repository=_Repository("Increases your Maximum Health by 1000."),
    ).build("max_health")

    assert audit.denominator_proven is True
    assert audit.objective_irrelevance_proven is False
    assert audit.relevant_glyphs == ("Glyph of Flame Resist",)
    assert audit.unresolved == ()
