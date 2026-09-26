from __future__ import annotations

from dataclasses import dataclass

import pytest

from models.build_model import PlayerBuild
from services.extreme_sustained_dps_potion_frontier_service import (
    ExtremeSustainedDPSPotionFrontierService,
)


@dataclass(frozen=True)
class _Update:
    value: str = "U50"


@dataclass(frozen=True)
class _Formula:
    canonical_id: str
    traits: tuple[str, ...]
    reagents: tuple[str, ...] = ()
    game_update: _Update = _Update()


class _Repository:
    def catalog(self):
        return type(
            "_Catalog",
            (),
            {
                "game_update": _Update(),
                "unresolved": (),
                "formulas": (
                    _Formula("formula:a", ("Restore Magicka", "Increase Spell Power")),
                    _Formula("formula:b", ("Increase Spell Power", "Restore Magicka")),
                    _Formula("formula:c", ("Restore Stamina", "Weapon Critical")),
                ),
            },
        )()


def test_potion_frontier_deduplicates_reagent_formulas_by_exact_trait_family() -> None:
    result = ExtremeSustainedDPSPotionFrontierService(_Repository()).frontier()

    assert result.denominator_proven is True
    assert result.candidate_count == 3  # no potion + two exact trait families
    assert result.families[0].selected_label == ""
    assert result.families[1].formula_ids == ("formula:a", "formula:b")


def test_potion_candidate_materializes_family_selection() -> None:
    candidate = ExtremeSustainedDPSPotionFrontierService(_Repository()).candidate_at(
        PlayerBuild(),
        1,
    )

    assert candidate.build.Potion.startswith("alchemy_family:u50:")
    assert set(candidate.family.traits) == {"Restore Magicka", "Increase Spell Power"}


def test_potion_invalid_index_fails_closed() -> None:
    service = ExtremeSustainedDPSPotionFrontierService(_Repository())
    with pytest.raises(IndexError):
        service.candidate_at(PlayerBuild(), 3)


def test_potion_frontier_rejects_boolean_candidate_index() -> None:
    service = ExtremeSustainedDPSPotionFrontierService(_Repository())

    with pytest.raises(TypeError, match="candidate index must be an integer"):
        service.candidate_at(PlayerBuild(), True)
