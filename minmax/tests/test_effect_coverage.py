from minmax.effect_coverage import analyze_effect_coverage
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType


def effect(
    name: str,
    source: str,
    *,
    category: SupportEffectCategory = SupportEffectCategory.BUFF,
    target: SupportTargetType = SupportTargetType.SELF,
    magnitude: float = 1.0,
    duration: float | None = 10.0,
    conditions: tuple[str, ...] = (),
    stacking: StackingBehavior = StackingBehavior.UNIQUE,
    exclusivity_group: str | None = None,
) -> SupportEffect:
    return SupportEffect(
        source=source,
        name=name,
        category=category,
        effect_type=name,
        target_type=target,
        magnitude=magnitude,
        duration=duration,
        conditions=conditions,
        stacking=stacking,
        exclusivity_group=exclusivity_group,
    )


def test_coverage_groups_same_logical_effect_and_preserves_sources():
    report = analyze_effect_coverage(
        [
            effect("major_test", "Skill A", target=SupportTargetType.GROUP, magnitude=10),
            effect("major_test", "Set B", target=SupportTargetType.GROUP, magnitude=12),
        ]
    )

    covered = report.by_name("major_test")
    assert covered is not None
    assert covered.covered
    assert covered.redundant
    assert covered.source_names == ("Skill A", "Set B")
    assert covered.max_magnitude == 12
    assert covered.max_duration == 10


def test_stacking_providers_are_not_called_redundant():
    report = analyze_effect_coverage(
        [
            effect("stacking_effect", "Skill A", stacking=StackingBehavior.STACKS),
            effect("stacking_effect", "Set B", stacking=StackingBehavior.STACKS),
        ]
    )

    covered = report.by_name("stacking_effect")
    assert covered is not None
    assert not covered.redundant


def test_conditional_effect_is_reported_as_conditional():
    report = analyze_effect_coverage(
        [
            effect(
                "conditional_debuff",
                "Skill A",
                category=SupportEffectCategory.DEBUFF,
                target=SupportTargetType.ENEMY,
                conditions=("target_is_chilled",),
            )
        ]
    )

    covered = report.by_name("conditional_debuff")
    assert covered is not None
    assert covered.covered
    assert covered.conditional
    assert covered.category == SupportEffectCategory.DEBUFF
    assert covered.target_types == (SupportTargetType.ENEMY,)


def test_missing_from_uses_logical_effect_identity():
    report = analyze_effect_coverage(
        [effect("major_breach", "Skill A", target=SupportTargetType.ENEMY)]
    )

    assert report.missing_from(("major_breach", "minor_breach")) == ("minor_breach",)
