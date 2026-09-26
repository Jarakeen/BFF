from __future__ import annotations

import pytest

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_jewelry_frontier_service import (
    ExtremeSustainedDPSJewelryFrontierService,
)


def _build():
    build = PlayerBuild()
    for field in ("Necklace", "Ring1", "Ring2"):
        slot = getattr(build, field)
        slot.Set = "Test Set"
        slot.Quality = "Gold"
        slot.Trait = "Bloodthirsty"
        slot.Enchant = "Weapon Damage"
    return build


def _service():
    return ExtremeSustainedDPSJewelryFrontierService(
        trait_choices=("Bloodthirsty", "Infused"),
        enchant_choices=("Weapon Damage", "Magicka Recovery"),
    )


def test_jewelry_frontier_counts_joint_product() -> None:
    result = _service().frontier(_build())

    assert result.denominator_proven is True
    assert len(result.slots) == 3
    assert result.candidate_count == 4 ** 3


def test_jewelry_candidate_indexing_is_deterministic() -> None:
    build = _build()
    first = _service().candidate_at(build, 0)
    last = _service().candidate_at(build, 4 ** 3 - 1)

    assert first.slot_choices[0] == ("Necklace", "Bloodthirsty", "Magicka Recovery")
    assert last.slot_choices[-1] == ("Ring2", "Infused", "Weapon Damage")


def test_jewelry_page_is_lazy() -> None:
    rows = _service().page(_build(), offset=5, limit=3)
    assert tuple(row.structural_index for row in rows) == (5, 6, 7)


def test_unequipped_jewelry_does_not_expand_denominator() -> None:
    build = _build()
    build.Ring2 = type(build.Ring2)()
    result = _service().frontier(build)

    assert tuple(row.slot for row in result.slots) == ("Necklace", "Ring1")
    assert result.candidate_count == 4 ** 2


def test_invalid_jewelry_index_fails_closed() -> None:
    with pytest.raises(IndexError):
        _service().candidate_at(_build(), -1)


def test_jewelry_frontier_rejects_boolean_candidate_index() -> None:
    with pytest.raises(TypeError, match="candidate index must be an integer"):
        _service().candidate_at(_build(), False)


@pytest.mark.parametrize("field,value", (("offset", False), ("limit", "3"), ("offset", 2.5)))
def test_jewelry_page_requires_strict_integer_bounds(field, value) -> None:
    kwargs = {"offset": 0, "limit": 3}
    kwargs[field] = value

    with pytest.raises(TypeError, match=f"jewelry page {field} must be an integer"):
        _service().page(_build(), **kwargs)


def test_jewelry_frontier_requires_tuple_choice_collections() -> None:
    with pytest.raises(TypeError, match="enchant choices must be a tuple"):
        ExtremeSustainedDPSJewelryFrontierService(
            trait_choices=("Bloodthirsty",),
            enchant_choices=["Weapon Damage"],  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="trait choices must be a tuple"):
        ExtremeSustainedDPSJewelryFrontierService(
            trait_choices=["Bloodthirsty"],  # type: ignore[arg-type]
            enchant_choices=("Weapon Damage",),
        )


def test_jewelry_frontier_rejects_non_string_choices() -> None:
    with pytest.raises(TypeError, match="must contain only strings"):
        ExtremeSustainedDPSJewelryFrontierService(
            trait_choices=("Bloodthirsty", 7),  # type: ignore[arg-type]
            enchant_choices=("Weapon Damage",),
        )
