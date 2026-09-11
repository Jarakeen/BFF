from __future__ import annotations

import pytest

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_armor_glyph_state_service import ExtremeArmorGlyphStateService


class _Repository:
    def __init__(self, *, extra_names=(), missing=()):
        self.extra_names = tuple(extra_names)
        self.missing = set(missing)

    def list_names(self):
        return (
            "Glyph of Health",
            "Glyph of Magicka",
            "Glyph of Stamina",
            "Glyph of Prismatic Defense",
            *self.extra_names,
        )

    def get_armor_glyph_effect_by_name(self, name, *, use_max_value=True):
        assert use_max_value is True
        if name in self.missing:
            return []
        mapping = {
            "Glyph of Health": ((StatId.MAX_HEALTH, 868.0),),
            "Glyph of Magicka": ((StatId.MAX_MAGICKA, 868.0),),
            "Glyph of Stamina": ((StatId.MAX_STAMINA, 868.0),),
            "Glyph of Prismatic Defense": (
                (StatId.MAX_HEALTH, 477.0),
                (StatId.MAX_MAGICKA, 434.0),
                (StatId.MAX_STAMINA, 434.0),
            ),
        }
        return [
            Effect(
                operation=EffectOperation.ADD,
                value=value,
                source=name,
                stat=stat,
            )
            for stat, value in mapping[name]
        ]


def test_max_health_keeps_health_and_prismatic_and_prunes_other_resolved_glyphs():
    catalog = ExtremeArmorGlyphStateService(repository=_Repository()).build("max_health")

    assert tuple(row.enchant_label for row in catalog.choices) == (
        "Max Health",
        "Prismatic Defense",
    )
    assert set(catalog.pruned_irrelevant_glyphs) == {
        "Glyph of Magicka",
        "Glyph of Stamina",
    }
    assert len(catalog.states) == 3**7
    assert catalog.denominator_proven is True


def test_prismatic_is_relevant_to_each_supported_resource_objective():
    service = ExtremeArmorGlyphStateService(repository=_Repository())

    for objective in ("max_health", "max_magicka", "max_stamina"):
        catalog = service.build(objective)
        assert "Prismatic Defense" in {row.enchant_label for row in catalog.choices}
        assert catalog.denominator_proven is True


def test_unmapped_canonical_armor_glyph_fails_closed_without_pruning_it_silently():
    catalog = ExtremeArmorGlyphStateService(
        repository=_Repository(extra_names=("Glyph of Mysterious Bureaucracy",))
    ).build("max_magicka")

    assert catalog.denominator_proven is False
    assert any("not covered" in item for item in catalog.unresolved)


def test_missing_known_glyph_effect_blocks_denominator_proof():
    catalog = ExtremeArmorGlyphStateService(
        repository=_Repository(missing=("Glyph of Prismatic Defense",))
    ).build("max_stamina")

    assert catalog.denominator_proven is False
    assert any("no canonical armor glyph effects found" in item for item in catalog.unresolved)


def test_materialization_sets_cp160_truly_superb_and_preserves_other_armor_axes():
    catalog = ExtremeArmorGlyphStateService(repository=_Repository()).build("max_health")
    state = next(
        row
        for row in catalog.states
        if dict(row.enchants)["Head"] == "Max Health"
        and all(
            enchant == ""
            for slot, enchant in row.enchants
            if slot != "Head"
        )
    )
    build = PlayerBuild()
    build.Armor["Head"].update(
        {
            "Set": "Trial Set",
            "Trait": "Infused",
            "Weight": "Heavy",
            "Quality": "Gold",
        }
    )

    materialized = ExtremeArmorGlyphStateService.materialize(build, state)

    assert materialized.Armor["Head"]["Set"] == "Trial Set"
    assert materialized.Armor["Head"]["Trait"] == "Infused"
    assert materialized.Armor["Head"]["Weight"] == "Heavy"
    assert materialized.Armor["Head"]["Quality"] == "Gold"
    assert materialized.Armor["Head"]["Enchant"] == "Max Health"
    assert materialized.Armor["Head"]["Level"] == "CP160"
    assert materialized.Armor["Head"]["EnchantTier"] == "Truly Superb"
    assert materialized.Armor["Chest"]["Enchant"] == ""
    assert materialized.Armor["Chest"]["Level"] == ""
    assert materialized.Armor["Chest"]["EnchantTier"] == ""


def test_unsupported_objective_fails_closed():
    with pytest.raises(KeyError, match="unreviewed Extreme armor glyph objective"):
        ExtremeArmorGlyphStateService(repository=_Repository()).build("spell_damage")
