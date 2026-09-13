from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphStateService,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphStateService,
)
from services.extreme_max_health_armor_scoring_frontier_service import (
    ExtremeMaxHealthArmorScoringFrontierService,
)


class _Repository:
    def resolve(self, _name):
        return (), ()


def test_max_health_frontier_retains_only_best_juggernaut_plus_mettle_signatures():
    trait_glyph = ExtremeArmorResourceTraitGlyphStateService(repository=_Repository()).build(
        "max_health"
    )
    catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        "max_health",
        trait_glyph_service=ExtremeArmorResourceTraitGlyphStateService(repository=_Repository()),
    ).build("max_health")

    assert catalog.denominator_proven
    assert len(catalog.weight_catalog.states) == 14

    frontier = ExtremeMaxHealthArmorScoringFrontierService.build(catalog)

    assert frontier.reduction_proven
    assert frontier.best_reviewed_percent == 0.16
    assert frontier.retained_weight_signatures == ((1, 7), (2, 6), (3, 5))
    assert len(frontier.states) == 3 * len(trait_glyph.states)
    assert frontier.states_pruned == len(catalog.states) - len(frontier.states)
