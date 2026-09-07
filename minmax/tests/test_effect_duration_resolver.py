import pytest

from minmax.character_build.effect_duration_resolver import EffectDurationResolver
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.support_effect_category import SupportEffectCategory


def _effect(
    name: str,
    *,
    duration: float | None,
    category: SupportEffectCategory,
    source: str = "Test source",
    magnitude: float | None = None,
    eligible: bool = True,
) -> EffectVariant:
    return EffectVariant(
        name=name,
        layer=EffectLayer.PASSIVE,
        source=source,
        duration=duration,
        magnitude=magnitude,
        category=category,
        eligible=eligible,
    )


def test_status_effect_uses_verified_serpents_disdain_duration_increase() -> None:
    status = _effect(
        "chilled",
        duration=4.0,
        category=SupportEffectCategory.STATUS,
        source="Chilled",
    )
    serpents_disdain = _effect(
        "status_effect_duration_increase",
        duration=None,
        magnitude=16.0,
        category=SupportEffectCategory.OTHER,
        source="Serpent's Disdain (5)",
    )

    resolved = EffectDurationResolver().resolve(
        status,
        available_effects=(serpents_disdain,),
    )

    assert resolved.base_duration_seconds == pytest.approx(4.0)
    assert resolved.effective_duration_seconds == pytest.approx(20.0)
    assert resolved.unresolved == ()
    assert len(resolved.applied_modifiers) == 1
    assert resolved.applied_modifiers[0].seconds == pytest.approx(16.0)
    assert resolved.applied_modifiers[0].source == "Serpent's Disdain (5)"


def test_status_duration_modifier_does_not_extend_non_status_skill_effect() -> None:
    ground_effect = _effect(
        "winter_ground_effect",
        duration=12.0,
        category=SupportEffectCategory.DEBUFF,
    )
    modifier = _effect(
        "status_effect_duration_increase",
        duration=None,
        magnitude=16.0,
        category=SupportEffectCategory.OTHER,
        source="Serpent's Disdain (5)",
    )

    resolved = EffectDurationResolver().resolve(
        ground_effect,
        available_effects=(modifier,),
    )

    assert resolved.effective_duration_seconds == pytest.approx(12.0)
    assert resolved.applied_modifiers == ()
    assert resolved.unresolved == ()


def test_ineligible_duration_modifier_is_not_applied() -> None:
    status = _effect("burning", duration=4.0, category=SupportEffectCategory.STATUS)
    modifier = _effect(
        "status_effect_duration_increase",
        duration=None,
        magnitude=16.0,
        category=SupportEffectCategory.OTHER,
        source="Inactive modifier",
        eligible=False,
    )

    resolved = EffectDurationResolver().resolve(
        status,
        available_effects=(modifier,),
    )

    assert resolved.effective_duration_seconds == pytest.approx(4.0)
    assert resolved.applied_modifiers == ()


def test_missing_base_effect_duration_remains_unresolved() -> None:
    status = _effect("chilled", duration=None, category=SupportEffectCategory.STATUS)

    resolved = EffectDurationResolver().resolve(status)

    assert resolved.effective_duration_seconds is None
    assert resolved.unresolved == ("chilled: base effect duration unresolved",)


def test_missing_modifier_magnitude_fails_closed() -> None:
    status = _effect("chilled", duration=4.0, category=SupportEffectCategory.STATUS)
    modifier = _effect(
        "status_effect_duration_increase",
        duration=None,
        magnitude=None,
        category=SupportEffectCategory.OTHER,
        source="Unresolved duration source",
    )

    resolved = EffectDurationResolver().resolve(
        status,
        available_effects=(modifier,),
    )

    assert resolved.effective_duration_seconds is None
    assert resolved.applied_modifiers == ()
    assert resolved.unresolved == (
        "chilled: Unresolved duration source has unresolved status-effect duration magnitude",
    )


def test_multiple_duration_modifiers_require_explicit_stacking_rule() -> None:
    status = _effect("chilled", duration=4.0, category=SupportEffectCategory.STATUS)
    first = _effect(
        "status_effect_duration_increase",
        duration=None,
        magnitude=16.0,
        category=SupportEffectCategory.OTHER,
        source="First verified source",
    )
    second = _effect(
        "status_effect_duration_increase",
        duration=None,
        magnitude=5.0,
        category=SupportEffectCategory.OTHER,
        source="Second verified source",
    )

    resolved = EffectDurationResolver().resolve(
        status,
        available_effects=(first, second),
    )

    assert resolved.effective_duration_seconds is None
    assert resolved.applied_modifiers == ()
    assert resolved.unresolved == (
        "chilled: multiple status-effect duration modifiers require explicit stacking "
        "resolution (First verified source, Second verified source)",
    )
