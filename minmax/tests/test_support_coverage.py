from minmax.build import Build
from minmax.build_combat_effect_service import BuildCombatEffectService
from minmax.build_support_effect_service import BuildSupportEffectService
from minmax.combat_effects import CombatEffect
from minmax.effects import EffectUnit
from minmax.role import Role
from minmax.support_coverage import SupportCoverage
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType


def _buff(
    *,
    source: str,
    name: str = "Major Courage",
    target_type: SupportTargetType = SupportTargetType.GROUP,
    role_relevance: frozenset[Role] = frozenset(),
    uptime: float = 1.0,
    stacking: StackingBehavior = StackingBehavior.UNIQUE,
    exclusivity_group: str | None = None,
) -> SupportEffect:
    return SupportEffect(
        source=source,
        name=name,
        category=SupportEffectCategory.BUFF,
        effect_type="weapon_spell_damage",
        target_type=target_type,
        role_relevance=role_relevance,
        uptime=uptime,
        stacking=stacking,
        exclusivity_group=exclusivity_group,
    )


def _debuff(
    *,
    source: str,
    name: str = "Major Breach",
    target_type: SupportTargetType = SupportTargetType.ENEMY,
    role_relevance: frozenset[Role] = frozenset(),
) -> SupportEffect:
    return SupportEffect(
        source=source,
        name=name,
        category=SupportEffectCategory.DEBUFF,
        effect_type="resistance_reduction",
        target_type=target_type,
        role_relevance=role_relevance,
    )


def _status(
    *,
    source: str,
    name: str,
    applies_status: str | None = None,
    requires_status: str | None = None,
) -> SupportEffect:
    return SupportEffect(
        source=source,
        name=name,
        category=SupportEffectCategory.STATUS,
        effect_type="status",
        target_type=SupportTargetType.ENEMY,
        applies_status=applies_status,
        requires_status=requires_status,
    )


def test_empty_coverage():
    coverage = SupportCoverage()

    assert len(coverage) == 0
    assert coverage.buffs == ()
    assert coverage.debuffs == ()
    assert coverage.statuses == ()
    assert coverage.sources() == ()


def test_one_supplied_buff():
    coverage = SupportCoverage.from_effects(
        [_buff(source="Healer A")],
    )

    assert len(coverage) == 1
    assert len(coverage.buffs) == 1
    assert coverage.debuffs == ()
    assert coverage.statuses == ()


def test_one_supplied_debuff():
    coverage = SupportCoverage.from_effects(
        [_debuff(source="Tank A")],
    )

    assert len(coverage.debuffs) == 1
    assert coverage.buffs == ()
    assert coverage.statuses == ()


def test_one_supplied_status():
    coverage = SupportCoverage.from_effects(
        [_status(source="Player A", name="Chilled", applies_status="Chilled")],
    )

    assert len(coverage.statuses) == 1
    assert coverage.buffs == ()
    assert coverage.debuffs == ()


def test_multiple_providers():
    coverage = SupportCoverage.from_effects(
        [
            _buff(source="Healer A", name="Major Courage"),
            _debuff(source="Tank A", name="Major Breach"),
        ],
    )

    assert set(coverage.sources()) == {"Healer A", "Tank A"}
    assert len(coverage.effects_for_source("Healer A")) == 1
    assert len(coverage.effects_for_source("Tank A")) == 1


def test_duplicate_overlapping_effects_preserve_both_sources():
    coverage = SupportCoverage.from_effects(
        [
            _debuff(source="Tank A", name="Major Breach"),
            _debuff(source="Tank B", name="Major Breach"),
        ],
    )

    overlapping = coverage.overlapping()

    assert len(overlapping) == 1
    group = overlapping[0]
    assert group.name == "Major Breach"
    assert set(group.sources) == {"Tank A", "Tank B"}
    assert len(group.effects) == 2
    assert group.is_overlapping is True

    # Both SupportEffect instances remain distinct, not collapsed.
    assert len(coverage) == 2


def test_non_overlapping_effects_are_not_reported_as_overlapping():
    coverage = SupportCoverage.from_effects(
        [
            _debuff(source="Tank A", name="Major Breach"),
            _buff(source="Healer A", name="Major Courage"),
        ],
    )

    assert coverage.overlapping() == ()


def test_missing_required_effects():
    coverage = SupportCoverage.from_effects(
        [
            _debuff(source="Tank A", name="Major Breach"),
            _buff(source="Healer A", name="Major Courage"),
        ],
    )

    missing = coverage.missing_from(
        ["Major Breach", "Brittle", "Major Courage"],
    )

    assert missing == ("Brittle",)


def test_missing_from_returns_empty_when_fully_covered():
    coverage = SupportCoverage.from_effects(
        [_debuff(source="Tank A", name="Major Breach")],
    )

    assert coverage.missing_from(["Major Breach"]) == ()


def test_target_filtering():
    coverage = SupportCoverage.from_effects(
        [
            _debuff(
                source="Tank A",
                name="Major Breach",
                target_type=SupportTargetType.ENEMY,
            ),
            _buff(
                source="Healer A",
                name="Major Courage",
                target_type=SupportTargetType.GROUP,
            ),
            _buff(
                source="DD A",
                name="Personal Power",
                target_type=SupportTargetType.SELF,
            ),
        ],
    )

    assert len(coverage.targeting_enemies()) == 1
    assert coverage.targeting_enemies()[0].name == "Major Breach"

    assert len(coverage.targeting_group()) == 1
    assert coverage.targeting_group()[0].name == "Major Courage"

    # SELF-targeted effects are not allies or the group.
    assert len(coverage.targeting_allies()) == 1


def test_role_filtering():
    coverage = SupportCoverage.from_effects(
        [
            _buff(
                source="Healer A",
                name="Major Courage",
                role_relevance=frozenset({Role.HEALER}),
            ),
            _debuff(
                source="Tank A",
                name="Major Breach",
                role_relevance=frozenset({Role.TANK}),
            ),
        ],
    )

    healer_effects = coverage.for_role(Role.HEALER)
    tank_effects = coverage.for_role(Role.TANK)
    dd_effects = coverage.for_role(Role.DD)

    assert len(healer_effects) == 1
    assert healer_effects[0].name == "Major Courage"

    assert len(tank_effects) == 1
    assert tank_effects[0].name == "Major Breach"

    assert dd_effects == ()


def test_source_provider_lookup():
    coverage = SupportCoverage.from_effects(
        [
            _debuff(source="Tank A", name="Major Breach"),
            _debuff(source="Tank B", name="Major Breach"),
            _buff(source="Healer A", name="Major Courage"),
        ],
    )

    assert set(coverage.sources_for_effect("Major Breach")) == {
        "Tank A",
        "Tank B",
    }
    assert coverage.sources_for_effect("Major Courage") == ("Healer A",)
    assert coverage.sources_for_effect("Nonexistent Effect") == ()


def test_uptime_is_preserved():
    coverage = SupportCoverage.from_effects(
        [_buff(source="Healer A", uptime=0.65)],
    )

    assert coverage.all()[0].uptime == 0.65


def test_stacking_and_exclusivity_are_preserved():
    coverage = SupportCoverage.from_effects(
        [
            _buff(
                source="Healer A",
                name="Major Brutality",
                stacking=StackingBehavior.UNIQUE,
                exclusivity_group="major_brutality",
            ),
        ],
    )

    effect = coverage.all()[0]
    assert effect.stacking == StackingBehavior.UNIQUE
    assert effect.exclusivity_group == "major_brutality"


def test_frost_chilled_brittle_remain_distinct():
    coverage = SupportCoverage.from_effects(
        [
            SupportEffect(
                source="Frost Staff",
                name="Frost Damage",
                category=SupportEffectCategory.OTHER,
                effect_type="damage",
                target_type=SupportTargetType.ENEMY,
            ),
            _status(
                source="Frost Staff",
                name="Chilled",
                applies_status="Chilled",
            ),
            SupportEffect(
                source="Frost Staff",
                name="Brittle",
                category=SupportEffectCategory.DEBUFF,
                effect_type="critical_damage_taken",
                target_type=SupportTargetType.ENEMY,
                requires_status="Chilled",
                applies_status="Brittle",
            ),
        ],
    )

    grouped = coverage.grouped_by_effect()

    assert {group.name for group in grouped} == {
        "Frost Damage",
        "Chilled",
        "Brittle",
    }
    # None of these are duplicates of one another.
    assert coverage.overlapping() == ()
    assert len(coverage.statuses) == 1
    assert len(coverage.debuffs) == 1


def test_multiple_effects_from_one_player():
    coverage = SupportCoverage.from_effects(
        [
            _debuff(source="Tank A", name="Major Breach"),
            _status(source="Tank A", name="Chilled", applies_status="Chilled"),
        ],
    )

    tank_effects = coverage.effects_for_source("Tank A")

    assert len(tank_effects) == 2
    assert {effect.name for effect in tank_effects} == {
        "Major Breach",
        "Chilled",
    }
    assert coverage.sources() == ("Tank A",)


def test_build_to_support_coverage_integration():
    """
    Build -> BuildSupportEffectService -> SupportEffectRegistry -> SupportCoverage
    """

    class FakeWeaponEnchantmentEffectService:
        def resolve_effects(
            self,
            enchantment_item_id: int,
            *,
            weapon_trait: str | None = None,
            weapon_quality: str | None = None,
            use_max_value: bool = True,
        ) -> list[CombatEffect]:
            return [
                CombatEffect(
                    effect_type="physical_spell_resistance_reduction",
                    value=2104,
                    source="Glyph of Crushing",
                    unit=EffectUnit.FLAT,
                    target="target",
                )
            ]

    combat_effect_service = BuildCombatEffectService(
        weapon_enchantment_service=FakeWeaponEnchantmentEffectService(),
    )
    support_effect_service = BuildSupportEffectService(
        build_combat_effect_service=combat_effect_service,
    )

    build = Build()
    build.add_weapon(enchantment_item_id=26845)

    registry = support_effect_service.resolve(build)
    coverage = SupportCoverage(registry)

    assert len(coverage) == 1
    assert coverage.debuffs[0].source == "Glyph of Crushing"
    assert len(coverage.targeting_enemies()) == 1
