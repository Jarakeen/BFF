from types import SimpleNamespace

from minmax.build_comparison import BuildComparison
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_effect_registry import SupportEffectRegistry
from minmax.support_target_type import SupportTargetType


class FakeResolver:
    def __init__(self, registries):
        self.registries = iter(registries)

    def resolve(self, *args, **kwargs):
        return next(self.registries)


def _effect(name, *, source="Test Source", magnitude=0.0):
    return SupportEffect(
        source=source,
        name=name,
        category=SupportEffectCategory.BUFF,
        effect_type=name,
        target_type=SupportTargetType.GROUP,
        magnitude=magnitude,
    )


def test_build_comparison_reports_added_removed_and_changed_effects():
    left = SupportEffectRegistry(
        [
            _effect("Major Courage"),
            _effect("Major Resolve", magnitude=10),
        ]
    )
    right = SupportEffectRegistry(
        [
            _effect("Major Courage"),
            _effect("Major Resolve", magnitude=20),
            _effect("Minor Brittle"),
        ]
    )

    result = BuildComparison(
        resolver=FakeResolver([left, right])
    ).compare(
        SimpleNamespace(name="General"),
        None,
        SimpleNamespace(name="Trial"),
        None,
    )

    assert result.shared_effects == ("Major Courage", "Major Resolve")
    assert result.added_effects == ("Minor Brittle",)
    assert result.removed_effects == ()
    assert result.changed_effects == ("Major Resolve",)
    assert result.changed
    assert result.net_effect_delta == 1


def test_build_comparison_can_report_removed_effects():
    left = SupportEffectRegistry([_effect("Major Courage")])
    right = SupportEffectRegistry([])

    result = BuildComparison(
        resolver=FakeResolver([left, right])
    ).compare(
        SimpleNamespace(name="A"),
        None,
        SimpleNamespace(name="B"),
        None,
    )

    assert result.removed_effects == ("Major Courage",)
    assert result.added_effects == ()
