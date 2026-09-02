import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_effect_targeting import resolve_effect_variant_runtime_targets


def _effect(**overrides):
    values = {
        "name": "test_effect",
        "layer": EffectLayer.PROC,
        "source": "Test Source",
    }
    values.update(overrides)
    return EffectVariant(**values)


def test_all_eligible_targets_are_selected_when_within_cap():
    result = resolve_effect_variant_runtime_targets(
        _effect(target_count=6),
        eligible_targets=("a", "b", "c", "d"),
    )
    assert result.resolved
    assert result.selected_targets == ("a", "b", "c", "d")


def test_selection_is_required_when_eligible_targets_exceed_cap():
    result = resolve_effect_variant_runtime_targets(
        _effect(target_count=2),
        eligible_targets=("a", "b", "c"),
    )
    assert not result.resolved
    assert result.selected_targets == ()
    assert result.unresolved == ("target_selection_required",)


def test_explicit_selection_resolves_over_cap_candidate_set():
    result = resolve_effect_variant_runtime_targets(
        _effect(target_count=2),
        eligible_targets=("a", "b", "c"),
        selected_targets=("c", "a"),
    )
    assert result.resolved
    assert result.selected_targets == ("c", "a")


def test_explicit_selection_cannot_exceed_cap():
    with pytest.raises(ValueError, match="exceeds"):
        resolve_effect_variant_runtime_targets(
            _effect(target_count=1),
            eligible_targets=("a", "b"),
            selected_targets=("a", "b"),
        )


def test_explicit_selection_must_be_subset_of_eligible_targets():
    with pytest.raises(ValueError, match="drawn from eligible"):
        resolve_effect_variant_runtime_targets(
            _effect(target_count=2),
            eligible_targets=("a", "b"),
            selected_targets=("a", "c"),
        )


def test_uncapped_effect_selects_all_supplied_eligible_targets():
    result = resolve_effect_variant_runtime_targets(
        _effect(target_count=None),
        eligible_targets=("a", "b", "c"),
    )
    assert result.resolved
    assert result.selected_targets == ("a", "b", "c")


def test_uncapped_effect_allows_explicit_runtime_subset():
    result = resolve_effect_variant_runtime_targets(
        _effect(target_count=None),
        eligible_targets=("a", "b", "c"),
        selected_targets=("b",),
    )
    assert result.resolved
    assert result.selected_targets == ("b",)


def test_zero_target_cap_requires_empty_selection():
    automatic = resolve_effect_variant_runtime_targets(
        _effect(target_count=0),
        eligible_targets=("a",),
    )
    assert not automatic.resolved
    assert automatic.unresolved == ("target_selection_required",)

    explicit = resolve_effect_variant_runtime_targets(
        _effect(target_count=0),
        eligible_targets=("a",),
        selected_targets=(),
    )
    assert explicit.resolved
    assert explicit.selected_targets == ()


def test_duplicate_or_blank_target_identities_are_rejected():
    with pytest.raises(ValueError, match="duplicate eligible"):
        resolve_effect_variant_runtime_targets(
            _effect(target_count=2),
            eligible_targets=("a", "a"),
        )
    with pytest.raises(ValueError, match="non-empty"):
        resolve_effect_variant_runtime_targets(
            _effect(target_count=2),
            eligible_targets=("a", " "),
        )
