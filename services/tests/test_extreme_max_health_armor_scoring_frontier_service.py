from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
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
    _effects = {
        "glyph of health": (
            Effect(EffectOperation.ADD, 100.0, "Glyph of Health", stat=StatId.MAX_HEALTH),
        ),
        "glyph of magicka": (
            Effect(EffectOperation.ADD, 100.0, "Glyph of Magicka", stat=StatId.MAX_MAGICKA),
        ),
        "glyph of stamina": (
            Effect(EffectOperation.ADD, 100.0, "Glyph of Stamina", stat=StatId.MAX_STAMINA),
        ),
        "glyph of prismatic defense": (
            Effect(EffectOperation.ADD, 90.0, "Glyph of Prismatic Defense", stat=StatId.MAX_HEALTH),
            Effect(EffectOperation.ADD, 90.0, "Glyph of Prismatic Defense", stat=StatId.MAX_MAGICKA),
            Effect(EffectOperation.ADD, 90.0, "Glyph of Prismatic Defense", stat=StatId.MAX_STAMINA),
        ),
    }

    def list_names(self):
        return (
            "Glyph of Health",
            "Glyph of Magicka",
            "Glyph of Stamina",
            "Glyph of Prismatic Defense",
        )

    def get_armor_glyph_effect_by_name(self, name, *, use_max_value=True):
        return list(self._effects.get(str(name).strip().casefold(), ()))


def test_max_health_frontier_retains_only_best_juggernaut_plus_mettle_signatures():
    trait_service = ExtremeArmorResourceTraitGlyphStateService(repository=_Repository())
    trait_glyph = trait_service.build("max_health")
    catalog = ExtremeArmorResourceWeightTraitGlyphStateService.from_services(
        "max_health",
        trait_glyph_service=trait_service,
    ).build("max_health")

    assert catalog.denominator_proven
    assert len(catalog.weight_catalog.states) == 14

    frontier = ExtremeMaxHealthArmorScoringFrontierService.build(catalog)

    assert frontier.reduction_proven
    assert frontier.best_reviewed_percent == 0.16
    assert frontier.retained_weight_signatures == ((1, 7), (2, 6), (3, 5))
    assert len(frontier.states) == 3 * len(trait_glyph.states)
    assert frontier.states_pruned == len(catalog.states) - len(frontier.states)
