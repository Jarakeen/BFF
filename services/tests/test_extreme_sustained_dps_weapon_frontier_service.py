from __future__ import annotations

import pytest

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_weapon_frontier_service import (
    ExtremeSustainedDPSWeaponFrontierService,
)


def _build():
    build = PlayerBuild()
    for field, weapon_type in (
        ("FrontBarWeapon", "Inferno Staff"),
        ("BackBarWeapon", "Inferno Staff"),
    ):
        slot = getattr(build, field)
        slot.Set = "Test Set"
        slot.WeaponType = weapon_type
        slot.Quality = "Gold"
        slot.Trait = "Precise"
        slot.Enchant = "Flame"
    return build


def _service():
    return ExtremeSustainedDPSWeaponFrontierService(
        trait_choices=("Precise", "Infused"),
        enchant_choices=("Flame", "Weapon Damage"),
    )


def test_weapon_frontier_counts_joint_product_and_marks_runtime_requirement() -> None:
    result = _service().frontier(_build())

    assert result.denominator_proven is True
    assert len(result.slots) == 2
    assert result.candidate_count == 4 ** 2
    assert result.runtime_evaluation_required is True


def test_weapon_candidate_preserves_runtime_requirement() -> None:
    candidate = _service().candidate_at(_build(), 0)

    assert candidate.runtime_evaluation_required is True
    assert candidate.slot_choices[0] == ("FrontBarWeapon", "Infused", "Flame")


def test_weapon_page_is_lazy() -> None:
    rows = _service().page(_build(), offset=2, limit=4)
    assert tuple(row.structural_index for row in rows) == (2, 3, 4, 5)


def test_unequipped_offhands_do_not_expand_denominator() -> None:
    result = _service().frontier(_build())

    assert tuple(row.slot for row in result.slots) == (
        "FrontBarWeapon",
        "BackBarWeapon",
    )


def test_invalid_weapon_index_fails_closed() -> None:
    with pytest.raises(IndexError):
        _service().candidate_at(_build(), 16)


def test_weapon_frontier_rejects_boolean_candidate_index() -> None:
    with pytest.raises(TypeError, match="candidate index must be an integer"):
        _service().candidate_at(_build(), True)


@pytest.mark.parametrize("field,value", (("offset", True), ("limit", "2"), ("offset", 1.5)))
def test_weapon_page_requires_strict_integer_bounds(field, value) -> None:
    kwargs = {"offset": 0, "limit": 2}
    kwargs[field] = value

    with pytest.raises(TypeError, match=f"weapon page {field} must be an integer"):
        _service().page(_build(), **kwargs)


def test_weapon_frontier_requires_tuple_choice_collections() -> None:
    with pytest.raises(TypeError, match="enchant choices must be a tuple"):
        ExtremeSustainedDPSWeaponFrontierService(
            trait_choices=("Precise",),
            enchant_choices=["Flame"],  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="trait choices must be a tuple"):
        ExtremeSustainedDPSWeaponFrontierService(
            trait_choices=["Precise"],  # type: ignore[arg-type]
            enchant_choices=("Flame",),
        )


def test_weapon_frontier_rejects_non_string_choices() -> None:
    with pytest.raises(TypeError, match="must contain only strings"):
        ExtremeSustainedDPSWeaponFrontierService(
            trait_choices=("Precise", 7),  # type: ignore[arg-type]
            enchant_choices=("Flame",),
        )
