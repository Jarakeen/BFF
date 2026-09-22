from __future__ import annotations

from dataclasses import dataclass

import pytest

from minmax.character_progression import AttributeAllocation
from services.extreme_sustained_dps_generated_candidate_service import (
    ExtremeSustainedDPSGeneratedFrontier,
    ExtremeSustainedDPSStructuralCandidate,
)
from services.extreme_sustained_dps_structural_family_adapter_service import (
    ExtremeSustainedDPSStructuralFamilyAdapterService,
)


@dataclass(frozen=True)
class _Route:
    name: str


class _Generated:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def frontier(self):
        return ExtremeSustainedDPSGeneratedFrontier(
            structural_candidate_count=len(self.rows),
            structural_denominator_proven=True,
            expanded_axes=(
                "race",
                "legal class route",
                "64-point attribute allocation",
                "active bar",
            ),
            deferred_axes=("gear",),
            evidence=(),
            unresolved=(),
        )

    def candidate_at(self, index):
        return self.rows[index]


def _candidate(index, *, race="Khajiit", route=None, health=0, magicka=64, stamina=0, bar="front"):
    return ExtremeSustainedDPSStructuralCandidate(
        structural_index=index,
        race=race,
        class_route=route or _Route("route"),
        attributes=AttributeAllocation(
            health=health,
            magicka=magicka,
            stamina=stamina,
        ),
        active_bar=bar,
    )


def test_collapses_valid_front_back_pair_into_one_structural_family() -> None:
    route = _Route("route")
    service = ExtremeSustainedDPSStructuralFamilyAdapterService(
        generated_candidates=_Generated(
            (
                _candidate(0, route=route, bar="front"),
                _candidate(1, route=route, bar="back"),
                _candidate(2, race="Dark Elf", route=route, bar="front"),
                _candidate(3, race="Dark Elf", route=route, bar="back"),
            )
        )
    )

    frontier = service.validate_denominator()
    choice = service.choice_at(1)
    proof = service.coverage()

    assert frontier.choice_count == 2
    assert frontier.denominator_proven is True
    assert choice.structural_family_index == 1
    assert choice.candidate.race == "Dark Elf"
    assert choice.candidate.active_bar == "front"
    assert choice.source_front_index == 2
    assert choice.source_back_index == 3
    assert proof.dominated_axes == ("race", "class_route", "attributes")


def test_pair_with_different_attributes_fails_denominator_validation() -> None:
    route = _Route("route")
    service = ExtremeSustainedDPSStructuralFamilyAdapterService(
        generated_candidates=_Generated(
            (
                _candidate(0, route=route, bar="front"),
                _candidate(1, route=route, magicka=0, stamina=64, bar="back"),
            )
        )
    )

    result = service.validate_denominator()

    assert result.denominator_proven is False
    assert service.coverage().dominated_axes == ()
    assert any("do not describe the same" in row for row in result.unresolved)


def test_pair_with_wrong_bar_order_fails_closed() -> None:
    route = _Route("route")
    service = ExtremeSustainedDPSStructuralFamilyAdapterService(
        generated_candidates=_Generated(
            (
                _candidate(0, route=route, bar="back"),
                _candidate(1, route=route, bar="front"),
            )
        )
    )

    with pytest.raises(ValueError, match="expected front coordinate first"):
        service.choice_at(0)
