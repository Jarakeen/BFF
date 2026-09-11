from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphStateService,
)
from services.extreme_armor_resource_weight_state_service import (
    ExtremeArmorResourceWeightStateService,
)
from services.extreme_armor_resource_weight_trait_glyph_state_service import (
    ExtremeArmorResourceWeightTraitGlyphStateService,
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


def _service(objective="max_health"):
    weight = ExtremeArmorResourceWeightStateService.build(objective)
    trait_glyph = ExtremeArmorResourceTraitGlyphStateService(
        repository=_Repository()
    ).build(objective)
    return ExtremeArmorResourceWeightTraitGlyphStateService(
        weight_catalog=weight,
        trait_glyph_catalog=trait_glyph,
    )


def test_combined_catalog_crosses_three_weight_witnesses_with_eight_trait_glyph_witnesses():
    catalog = _service().build("max_health")

    assert catalog.denominator_proven
    assert len(catalog.weight_catalog.states) == 3
    assert len(catalog.trait_glyph_catalog.states) == 8
    assert len(catalog.states) == 24
    assert {row.armor_type_count for row in catalog.states} == {1, 2, 3}
    assert {row.divines_count for row in catalog.states} == set(range(8))


def test_each_weight_count_preserves_all_divines_counts():
    catalog = _service().build("max_health")

    for armor_type_count in (1, 2, 3):
        rows = [row for row in catalog.states if row.armor_type_count == armor_type_count]
        assert len(rows) == 8
        assert {row.divines_count for row in rows} == set(range(8))


def test_materialization_preserves_sets_while_applying_weight_trait_and_glyph():
    catalog = _service().build("max_health")
    state = next(
        row
        for row in catalog.states
        if row.armor_type_count == 3 and row.divines_count == 0
    )
    build = PlayerBuild()
    for slot in build.Armor:
        build.Armor[slot]["Set"] = "Test Set"

    materialized = ExtremeArmorResourceWeightTraitGlyphStateService.materialize(build, state)

    assert {entry["Set"] for entry in materialized.Armor.values()} == {"Test Set"}
    assert {
        entry["Weight"] for entry in materialized.Armor.values()
    } == {"Light", "Medium", "Heavy"}
    assert {entry["Trait"] for entry in materialized.Armor.values()} == {"Infused"}
    assert {entry["Enchant"] for entry in materialized.Armor.values()} == {"Max Health"}
    assert {entry["Quality"] for entry in materialized.Armor.values()} == {"Gold"}


def test_catalog_objective_mismatch_fails_closed():
    service = _service("max_health")

    try:
        service.build("max_magicka")
    except ValueError as exc:
        assert "objective mismatch" in str(exc)
    else:
        raise AssertionError("expected combined resource armor objective mismatch")


def test_unreviewed_objective_fails_closed():
    service = _service("max_health")

    try:
        service.build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme resource armor weight/trait/glyph objective" in str(exc)
    else:
        raise AssertionError("expected unsupported combined resource armor objective")
