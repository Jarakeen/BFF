from __future__ import annotations

"""Lazy canonical jewelry trait/enchant frontier for sustained-DPS search."""

from dataclasses import dataclass

from models.build_model import JEWELRY_TRAITS, PlayerBuild
from services.build_enchant_catalog_service import BuildEnchantCatalogService


_JEWELRY_FIELDS = ("Necklace", "Ring1", "Ring2")


@dataclass(frozen=True)
class ExtremeSustainedDPSJewelrySlotAxis:
    slot: str
    trait_choices: tuple[str, ...]
    enchant_choices: tuple[str, ...]

    @property
    def choice_count(self) -> int:
        return len(self.trait_choices) * len(self.enchant_choices)


@dataclass(frozen=True)
class ExtremeSustainedDPSJewelryCandidate:
    structural_index: int
    slot_choices: tuple[tuple[str, str, str], ...]
    build: PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSJewelryFrontier:
    slots: tuple[ExtremeSustainedDPSJewelrySlotAxis, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.slots, tuple):
            raise TypeError("jewelry frontier slots must be a tuple")
        if isinstance(self.candidate_count, bool) or not isinstance(self.candidate_count, int):
            raise TypeError("jewelry frontier candidate_count must be an integer")
        if self.candidate_count < 0:
            raise ValueError("jewelry frontier candidate_count cannot be negative")
        if not isinstance(self.denominator_proven, bool):
            raise TypeError("jewelry frontier denominator_proven must be boolean")
        if not isinstance(self.evidence, tuple):
            raise TypeError("jewelry frontier evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("jewelry frontier unresolved must be a tuple")


class ExtremeSustainedDPSJewelryFrontierService:
    """Preserve the complete modeled jewelry trait × canonical glyph-family product."""

    def __init__(
        self,
        *,
        enchant_choices: tuple[str, ...],
        trait_choices: tuple[str, ...] | None = None,
    ) -> None:
        if not isinstance(enchant_choices, tuple):
            raise TypeError("jewelry enchant choices must be a tuple")
        if trait_choices is not None and not isinstance(trait_choices, tuple):
            raise TypeError("jewelry trait choices must be a tuple")
        self.enchant_choices = self._clean(enchant_choices)
        self.trait_choices = self._clean(
            trait_choices if trait_choices is not None else tuple(JEWELRY_TRAITS)
        )

    @classmethod
    def from_database(cls, database_path) -> "ExtremeSustainedDPSJewelryFrontierService":
        choices = tuple(
            item for item in BuildEnchantCatalogService(database_path).jewelry_choices()
            if str(item or "").strip()
        )
        return cls(enchant_choices=choices)

    def frontier(self, baseline_build: PlayerBuild) -> ExtremeSustainedDPSJewelryFrontier:
        unresolved: list[str] = []
        slots: list[ExtremeSustainedDPSJewelrySlotAxis] = []

        if not self.trait_choices:
            unresolved.append("Canonical jewelry trait denominator is empty")
        if not self.enchant_choices:
            unresolved.append("Canonical jewelry enchant denominator is empty")

        for field in _JEWELRY_FIELDS:
            slot = getattr(baseline_build, field)
            if slot.is_empty:
                continue
            slots.append(
                ExtremeSustainedDPSJewelrySlotAxis(
                    slot=field,
                    trait_choices=self.trait_choices,
                    enchant_choices=self.enchant_choices,
                )
            )

        if not slots:
            unresolved.append("No equipped jewelry slots are available for sustained-DPS search")

        count = 1
        for axis in slots:
            count *= axis.choice_count

        proven = bool(slots and count > 0 and not unresolved)
        return ExtremeSustainedDPSJewelryFrontier(
            slots=tuple(slots),
            candidate_count=count,
            denominator_proven=proven,
            evidence=(
                f"Equipped jewelry slots in frontier: {len(slots)}",
                f"Modeled jewelry traits per equipped slot: {len(self.trait_choices)}",
                f"Canonical jewelry glyph families per equipped slot: {len(self.enchant_choices)}",
                f"Lazy jewelry trait/enchant denominator: {count}",
                "No independent-stat DPS reduction is assumed",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def candidate_at(
        self,
        baseline_build: PlayerBuild,
        index: int,
    ) -> ExtremeSustainedDPSJewelryCandidate:
        frontier = self.frontier(baseline_build)
        if not frontier.denominator_proven:
            raise ValueError(
                "jewelry frontier denominator is unresolved: " + "; ".join(frontier.unresolved)
            )

        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("jewelry candidate index must be an integer")
        target = index
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("jewelry candidate index out of range")

        remainder = target
        selected_reversed: list[tuple[str, str, str]] = []
        for axis in reversed(frontier.slots):
            local_count = axis.choice_count
            local = remainder % local_count
            remainder //= local_count
            enchant_count = len(axis.enchant_choices)
            selected_reversed.append(
                (
                    axis.slot,
                    axis.trait_choices[local // enchant_count],
                    axis.enchant_choices[local % enchant_count],
                )
            )

        selected = tuple(reversed(selected_reversed))
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        for field, trait, enchant in selected:
            slot = getattr(build, field)
            slot.Trait = trait
            slot.Enchant = enchant

        return ExtremeSustainedDPSJewelryCandidate(
            structural_index=target,
            slot_choices=selected,
            build=build,
        )

    def page(
        self,
        baseline_build: PlayerBuild,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ExtremeSustainedDPSJewelryCandidate, ...]:
        frontier = self.frontier(baseline_build)
        if isinstance(offset, bool) or not isinstance(offset, int):
            raise TypeError("jewelry page offset must be an integer")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("jewelry page limit must be an integer")
        start = max(0, offset)
        size = max(0, limit)
        if size == 0 or start >= frontier.candidate_count:
            return ()
        return tuple(
            self.candidate_at(baseline_build, index)
            for index in range(start, min(frontier.candidate_count, start + size))
        )

    @staticmethod
    def _clean(values: tuple[str, ...]) -> tuple[str, ...]:
        if not isinstance(values, tuple):
            raise TypeError("jewelry frontier choices must be a tuple")
        if any(not isinstance(value, str) for value in values):
            raise TypeError("jewelry frontier choices must contain only strings")
        unique = {
            " ".join(value.strip().split())
            for value in values
            if value.strip()
        }
        return tuple(sorted(unique, key=str.casefold))


__all__ = [
    "ExtremeSustainedDPSJewelryCandidate",
    "ExtremeSustainedDPSJewelryFrontier",
    "ExtremeSustainedDPSJewelryFrontierService",
    "ExtremeSustainedDPSJewelrySlotAxis",
]
