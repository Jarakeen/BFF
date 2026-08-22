from minmax.role import Role
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_effect_registry import SupportEffectRegistry
from minmax.support_target_type import SupportTargetType


def _registry() -> SupportEffectRegistry:
    return SupportEffectRegistry(
        [
            SupportEffect(
                source="Healer",
                name="Major Courage",
                category=SupportEffectCategory.BUFF,
                effect_type="weapon_spell_damage",
                target_type=SupportTargetType.GROUP,
                role_relevance=frozenset({Role.HEALER}),
            ),
            SupportEffect(
                source="Tank",
                name="Major Breach",
                category=SupportEffectCategory.DEBUFF,
                effect_type="resistance_reduction",
                target_type=SupportTargetType.ENEMY,
                role_relevance=frozenset({Role.TANK}),
            ),
            SupportEffect(
                source="Tank",
                name="Chilled",
                category=SupportEffectCategory.STATUS,
                effect_type="status",
                target_type=SupportTargetType.ENEMY,
                applies_status="Chilled",
                role_relevance=frozenset({Role.TANK, Role.DD}),
            ),
            SupportEffect(
                source="DD",
                name="Personal Weapon Damage",
                category=SupportEffectCategory.BUFF,
                effect_type="weapon_damage",
                target_type=SupportTargetType.SELF,
                role_relevance=frozenset({Role.DD}),
            ),
        ]
    )


def test_registry_reports_effects_for_a_source():
    registry = _registry()

    tank_effects = registry.for_source("Tank")

    assert len(tank_effects) == 2
    assert {effect.name for effect in tank_effects} == {
        "Major Breach",
        "Chilled",
    }


def test_registry_filters_buffs():
    registry = _registry()

    buffs = registry.buffs()

    assert len(buffs) == 2
    assert all(
        effect.category == SupportEffectCategory.BUFF
        for effect in buffs
    )


def test_registry_filters_debuffs():
    registry = _registry()

    debuffs = registry.debuffs()

    assert len(debuffs) == 1
    assert debuffs[0].name == "Major Breach"


def test_registry_filters_statuses():
    registry = _registry()

    statuses = registry.statuses()

    assert len(statuses) == 1
    assert statuses[0].name == "Chilled"


def test_registry_filters_effects_targeting_enemies():
    registry = _registry()

    enemy_effects = registry.targeting_enemies()

    assert {effect.name for effect in enemy_effects} == {
        "Major Breach",
        "Chilled",
    }


def test_registry_filters_effects_targeting_allies():
    registry = _registry()

    ally_effects = registry.targeting_allies()

    assert len(ally_effects) == 1
    assert ally_effects[0].name == "Major Courage"


def test_registry_filters_by_role():
    registry = _registry()

    healer_effects = registry.for_role(Role.HEALER)
    tank_effects = registry.for_role(Role.TANK)

    assert len(healer_effects) == 1
    assert healer_effects[0].name == "Major Courage"

    assert {effect.name for effect in tank_effects} == {
        "Major Breach",
        "Chilled",
    }


def test_registry_reports_effects_contributing_to_group():
    registry = _registry()

    contributing = registry.contributing_to_group()

    assert {effect.name for effect in contributing} == {
        "Major Courage",
        "Major Breach",
        "Chilled",
    }


def test_add_extends_registry():
    registry = SupportEffectRegistry()

    registry.add(
        SupportEffect(
            source="New Source",
            name="New Buff",
            category=SupportEffectCategory.BUFF,
            effect_type="weapon_spell_damage",
            target_type=SupportTargetType.GROUP,
        )
    )

    assert len(registry) == 1
    assert registry.all()[0].name == "New Buff"
