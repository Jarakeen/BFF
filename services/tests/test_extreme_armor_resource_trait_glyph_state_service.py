from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphStateService,
)


class _Repository:
    _effects = {
        "glyph of health": (Effect(EffectOperation.ADD, 100.0, "Glyph of Health", stat=StatId.MAX_HEALTH),),
        "glyph of magicka": (Effect(EffectOperation.ADD, 100.0, "Glyph of Magicka", stat=StatId.MAX_MAGICKA),),
        "glyph of stamina": (Effect(EffectOperation.ADD, 100.0, "Glyph of Stamina", stat=StatId.MAX_STAMINA),),
        "glyph of prismatic defense": (
            Effect(EffectOperation.ADD, 90.0, "Glyph of Prismatic Defense", stat=StatId.MAX_HEALTH),
            Effect(EffectOperation.ADD, 90.0, "Glyph of Prismatic Defense", stat=StatId.MAX_MAGICKA),
            Effect(EffectOperation.ADD, 90.0, "Glyph of Prismatic Defense", stat=StatId.MAX_STAMINA),
        ),
    }

    def list_names(self):
        return tuple(
            {
                "Glyph of Health",
                "Glyph of Magicka",
                "Glyph of Stamina",
                "Glyph of Prismatic Defense",
            }
        )

    def get_armor_glyph_effect_by_name(self, name, *, use_max_value=True):
        return list(self._effects.get(str(name).strip().casefold(), ()))


class _UnknownRepository(_Repository):
    def list_names(self):
        return (*super().list_names(), "Glyph of Mystery")


def test_joint_catalog_reduces_to_one_witness_per_divines_count():
    catalog = ExtremeArmorResourceTraitGlyphStateService(repository=_Repository()).build("max_health")

    assert catalog.denominator_proven
    assert tuple(state.divines_count for state in catalog.states) == tuple(range(8))
    assert len(catalog.states) == 8
    assert catalog.glyph_choices_reviewed == 2
    assert catalog.dominated_states_pruned > 0


def test_zero_divines_uses_infused_strongest_resource_glyph_on_every_slot():
    catalog = ExtremeArmorResourceTraitGlyphStateService(repository=_Repository()).build("max_health")
    state = next(row for row in catalog.states if row.divines_count == 0)

    assert state.infused_count == 7
    assert {piece.enchant for piece in state.pieces} == {"Max Health"}
    # 3 major slots at 100 * 1.25 plus 4 minor slots at 100 * .4 * 1.25.
    assert state.direct_glyph_delta == 575.0


def test_seven_divines_keeps_glyphs_because_divines_and_enchants_can_coexist():
    catalog = ExtremeArmorResourceTraitGlyphStateService(repository=_Repository()).build("max_health")
    state = next(row for row in catalog.states if row.divines_count == 7)

    assert state.infused_count == 0
    assert {piece.trait for piece in state.pieces} == {"Divines"}
    assert {piece.enchant for piece in state.pieces} == {"Max Health"}
    assert state.direct_glyph_delta == 460.0


def test_materialization_preserves_set_and_weight_while_applying_trait_and_glyph_state():
    catalog = ExtremeArmorResourceTraitGlyphStateService(repository=_Repository()).build("max_health")
    state = next(row for row in catalog.states if row.divines_count == 0)
    build = PlayerBuild()
    for slot in build.Armor:
        build.Armor[slot]["Set"] = "Test Set"
        build.Armor[slot]["Weight"] = "Heavy"

    materialized = ExtremeArmorResourceTraitGlyphStateService.materialize(build, state)

    for slot in materialized.Armor:
        entry = materialized.Armor[slot]
        assert entry["Set"] == "Test Set"
        assert entry["Weight"] == "Heavy"
        assert entry["Trait"] == "Infused"
        assert entry["Quality"] == "Gold"
        assert entry["Enchant"] == "Max Health"
        assert entry["Level"] == "CP160"
        assert entry["EnchantTier"] == "Truly Superb"


def test_unknown_canonical_glyph_blocks_denominator_proof():
    catalog = ExtremeArmorResourceTraitGlyphStateService(repository=_UnknownRepository()).build("max_health")

    assert not catalog.denominator_proven
    assert any("Glyph of Mystery" in row for row in catalog.unresolved)


def test_unreviewed_objective_fails_closed():
    try:
        ExtremeArmorResourceTraitGlyphStateService(repository=_Repository()).build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme armor resource trait/glyph objective" in str(exc)
    else:
        raise AssertionError("expected unsupported joint trait/glyph objective to fail closed")
