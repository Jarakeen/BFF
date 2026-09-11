from services.extreme_jewelry_resource_glyph_relevance_service import (
    ExtremeJewelryResourceGlyphRelevanceService,
)


class _SemanticRepository:
    def list_names(self):
        return (
            "Glyph of Bracing",
            "Glyph of Potion Speed",
            "Glyph of Impossible Health",
        )

    def get_jewelry_glyph_effect_types_by_name(self, name):
        rows = {
            "Glyph of Bracing": ("block_cost_reduction",),
            "Glyph of Potion Speed": ("potion_cooldown_reduction",),
            "Glyph of Impossible Health": ("max_health",),
        }
        return rows[name]


def test_semantic_non_core_effects_are_irrelevant_to_max_health_without_engine_mapping():
    audit = ExtremeJewelryResourceGlyphRelevanceService(
        repository=_SemanticRepository()
    ).build("max_magicka")

    assert audit.denominator_proven is True
    assert audit.objective_irrelevance_proven is True
    assert audit.relevant_glyphs == ()
    assert audit.unresolved == ()


def test_semantic_resource_effect_still_blocks_resource_irrelevance():
    audit = ExtremeJewelryResourceGlyphRelevanceService(
        repository=_SemanticRepository()
    ).build("max_health")

    assert audit.denominator_proven is True
    assert audit.objective_irrelevance_proven is False
    assert audit.relevant_glyphs == ("Glyph of Impossible Health",)
