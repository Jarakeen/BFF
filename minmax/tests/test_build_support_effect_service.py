from minmax.build import Build
from minmax.build_combat_effect_service import BuildCombatEffectService
from minmax.build_support_effect_service import BuildSupportEffectService
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_effect_registry import SupportEffectRegistry
from minmax.support_target_type import SupportTargetType


CRUSHING_ITEM_ID = 26845
FROST_ITEM_ID = 5365
ABSORB_HEALTH_ITEM_ID = 43573


class FakeWeaponEnchantmentEffectService:
    """
    A duck-typed stand-in for WeaponEnchantmentEffectService that returns
    canned CombatEffects instead of touching the real ESO database, the
    same way the project's other fake/manual test doubles work.
    """

    def __init__(self, effects_by_item_id: dict[int, list[CombatEffect]]):
        self.effects_by_item_id = effects_by_item_id

    def resolve_effects(
        self,
        enchantment_item_id: int,
        *,
        weapon_trait: str | None = None,
        weapon_quality: str | None = None,
        use_max_value: bool = True,
    ) -> list[CombatEffect]:
        return list(self.effects_by_item_id.get(enchantment_item_id, []))


def _service(
    effects_by_item_id: dict[int, list[CombatEffect]],
) -> BuildSupportEffectService:
    fake_weapon_service = FakeWeaponEnchantmentEffectService(
        effects_by_item_id,
    )

    combat_effect_service = BuildCombatEffectService(
        weapon_enchantment_service=fake_weapon_service,
    )

    return BuildSupportEffectService(
        build_combat_effect_service=combat_effect_service,
    )


def _crushing_effect() -> CombatEffect:
    return CombatEffect(
        effect_type="physical_spell_resistance_reduction",
        value=2104,
        source="Glyph of Crushing",
        unit=EffectUnit.FLAT,
        target="target",
        duration_value=5,
        duration_unit="seconds",
    )


def _frost_damage_effect() -> CombatEffect:
    return CombatEffect(
        effect_type="damage",
        value=2534,
        source="Glyph of Frost",
        unit=EffectUnit.FLAT,
        damage_type="frost",
    )


def _absorb_health_effect() -> CombatEffect:
    return CombatEffect(
        effect_type="health_restore",
        value=1200,
        source="Glyph of Absorb Health",
        unit=EffectUnit.FLAT,
    )


def test_empty_build_produces_empty_registry():
    service = _service({})

    registry = service.resolve(Build())

    assert isinstance(registry, SupportEffectRegistry)
    assert len(registry) == 0


def test_build_with_resolvable_support_effect_produces_it():
    service = _service({CRUSHING_ITEM_ID: [_crushing_effect()]})

    build = Build()
    build.add_weapon(enchantment_item_id=CRUSHING_ITEM_ID)

    registry = service.resolve(build)

    assert len(registry) == 1


def test_registry_preserves_source():
    service = _service({CRUSHING_ITEM_ID: [_crushing_effect()]})

    build = Build()
    build.add_weapon(enchantment_item_id=CRUSHING_ITEM_ID)

    registry = service.resolve(build)

    assert registry.all()[0].source == "Glyph of Crushing"


def test_target_type_is_preserved():
    service = _service({CRUSHING_ITEM_ID: [_crushing_effect()]})

    build = Build()
    build.add_weapon(enchantment_item_id=CRUSHING_ITEM_ID)

    registry = service.resolve(build)

    assert registry.all()[0].target_type == SupportTargetType.ENEMY
    assert len(registry.targeting_enemies()) == 1


def test_debuff_category_is_preserved():
    service = _service({CRUSHING_ITEM_ID: [_crushing_effect()]})

    build = Build()
    build.add_weapon(enchantment_item_id=CRUSHING_ITEM_ID)

    registry = service.resolve(build)

    assert registry.all()[0].category == SupportEffectCategory.DEBUFF
    assert len(registry.debuffs()) == 1
    assert len(registry.buffs()) == 0
    assert len(registry.statuses()) == 0


def test_role_relevance_is_not_fabricated():
    """
    Build has no role/class data today, so role_relevance must stay
    empty rather than being guessed at.
    """

    service = _service({CRUSHING_ITEM_ID: [_crushing_effect()]})

    build = Build()
    build.add_weapon(enchantment_item_id=CRUSHING_ITEM_ID)

    registry = service.resolve(build)

    assert registry.all()[0].role_relevance == frozenset()


def test_multiple_support_effects_from_one_build():
    other_item_id = 99999

    service = _service(
        {
            CRUSHING_ITEM_ID: [_crushing_effect()],
            other_item_id: [
                CombatEffect(
                    effect_type="physical_spell_resistance_reduction",
                    value=500,
                    source="Another Debuff Enchant",
                    unit=EffectUnit.FLAT,
                    target="target",
                )
            ],
        }
    )

    build = Build()
    build.add_weapon(enchantment_item_id=CRUSHING_ITEM_ID)
    build.add_weapon(enchantment_item_id=other_item_id)

    registry = service.resolve(build)

    assert len(registry) == 2
    assert {effect.source for effect in registry.all()} == {
        "Glyph of Crushing",
        "Another Debuff Enchant",
    }


def test_plain_damage_enchantment_is_not_a_support_effect():
    service = _service({FROST_ITEM_ID: [_frost_damage_effect()]})

    build = Build()
    build.add_weapon(enchantment_item_id=FROST_ITEM_ID)

    registry = service.resolve(build)

    assert len(registry) == 0


def test_healing_enchantment_is_not_a_support_effect():
    service = _service(
        {ABSORB_HEALTH_ITEM_ID: [_absorb_health_effect()]}
    )

    build = Build()
    build.add_weapon(enchantment_item_id=ABSORB_HEALTH_ITEM_ID)

    registry = service.resolve(build)

    assert len(registry) == 0


def test_unsupported_build_components_are_ignored_not_guessed():
    """
    Gear sets and armor glyphs are not yet resolvable into SupportEffects,
    so a build that only has those should produce an empty registry
    rather than fabricated effects.
    """

    service = _service({})

    build = Build()
    build.add_gear_set(set_id=123, piece_count=5)
    build.add_armor_glyph(item_id=456)

    registry = service.resolve(build)

    assert len(registry) == 0


def test_returned_object_is_a_support_effect_registry():
    service = _service({})

    registry = service.resolve(Build())

    assert isinstance(registry, SupportEffectRegistry)
