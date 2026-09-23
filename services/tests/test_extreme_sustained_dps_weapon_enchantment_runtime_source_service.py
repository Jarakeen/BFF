from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from models.build_model import GearSlot, PlayerBuild
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceService,
)


class _Repository:
    def __init__(self, matches=(43573,), identity="Absorb Health"):
        self.matches = tuple(matches)
        self.identity = identity

    def find_item_ids_by_label(self, _label):
        return self.matches

    def get_identity_label(self, _item_id):
        return self.identity


class _Effects:
    def __init__(self, rows):
        self.rows = tuple(rows)
        self.calls = []

    def resolve_effects(self, item_id, **kwargs):
        self.calls.append((item_id, kwargs))
        return list(self.rows)


def _absorb_rows():
    return (
        CombatEffect(
            effect_type="damage",
            value=1900.0,
            source="Glyph of Absorb Health",
            unit=EffectUnit.FLAT,
            damage_type="magic",
        ),
        CombatEffect(
            effect_type="health_restore",
            value=861.0,
            source="Glyph of Absorb Health",
            unit=EffectUnit.FLAT,
        ),
    )


def test_runtime_source_preserves_one_enchant_with_multiple_consequences():
    effects = _Effects(_absorb_rows())
    service = ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceService(
        repository=_Repository(),
        effect_service=effects,
    )
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            Enchant="Absorb Health",
            Trait="Infused",
            Quality="Gold",
            EnchantTier="Truly Superb",
            EnchantQuality="Gold",
            Level="CP160",
        )
    )

    result = service.resolve(build)

    assert result.resolved is True
    assert len(result.sources) == 1
    source = result.sources[0]
    assert source.identity == "absorb_health"
    assert source.identity_label == "Absorb Health"
    assert source.source_label == "Glyph of Absorb Health"
    assert source.source_slot == "main_hand"
    assert source.weapon_trait == "Infused"
    assert source.weapon_quality == "Gold"
    assert source.enchantment_tier == "Truly Superb"
    assert source.enchantment_quality == "Gold"
    assert source.item_level == "CP160"
    assert len(source.effects) == 2
    assert effects.calls == [
        (
            43573,
            {"weapon_trait": "Infused", "weapon_quality": "Gold"},
        )
    ]
    assert any("consequence rows: 2" in row for row in result.evidence)


def test_runtime_source_fails_closed_on_ambiguous_saved_label():
    service = ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceService(
        repository=_Repository(matches=(1, 2)),
        effect_service=_Effects(_absorb_rows()),
    )
    build = PlayerBuild(FrontBarWeapon=GearSlot(Enchant="Ambiguous"))

    result = service.resolve(build)

    assert result.sources == ()
    assert any("ambiguous (2 matches)" in row for row in result.unresolved)


def test_runtime_source_fails_closed_without_canonical_identity_label():
    service = ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceService(
        repository=_Repository(identity=""),
        effect_service=_Effects(_absorb_rows()),
    )
    build = PlayerBuild(FrontBarWeapon=GearSlot(Enchant="Absorb Health"))

    result = service.resolve(build)

    assert result.sources == ()
    assert any("lacks canonical enchant identity" in row for row in result.unresolved)


def test_runtime_source_requires_all_consequences_to_share_one_canonical_source():
    rows = (
        CombatEffect(
            effect_type="damage",
            value=100.0,
            source="Glyph A",
            unit=EffectUnit.FLAT,
        ),
        CombatEffect(
            effect_type="health_restore",
            value=50.0,
            source="Glyph B",
            unit=EffectUnit.FLAT,
        ),
    )
    service = ExtremeSustainedDPSWeaponEnchantmentRuntimeSourceService(
        repository=_Repository(),
        effect_service=_Effects(rows),
    )
    build = PlayerBuild(FrontBarWeapon=GearSlot(Enchant="Absorb Health"))

    result = service.resolve(build)

    assert result.sources == ()
    assert any("do not share one canonical source label" in row for row in result.unresolved)
