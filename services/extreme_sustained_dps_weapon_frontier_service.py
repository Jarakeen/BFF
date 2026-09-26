from __future__ import annotations

"""Lazy canonical weapon trait/enchant frontier for sustained-DPS search.

Weapon enchantments are runtime combat effects. This service enumerates identities
only and deliberately does not score their damage or uptime.
"""

from dataclasses import dataclass

from models.build_model import WEAPON_TRAITS, PlayerBuild
from services.build_enchant_catalog_service import BuildEnchantCatalogService


_WEAPON_FIELDS = (
    "FrontBarWeapon",
    "FrontBarOffHand",
    "BackBarWeapon",
    "BackBarOffHand",
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponSlotAxis:
    slot: str
    trait_choices: tuple[str, ...]
    enchant_choices: tuple[str, ...]

    @property
    def choice_count(self) -> int:
        return len(self.trait_choices) * len(self.enchant_choices)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponCandidate:
    structural_index: int
    slot_choices: tuple[tuple[str, str, str], ...]
    build: PlayerBuild
    runtime_evaluation_required: bool = True


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponFrontier:
    slots: tuple[ExtremeSustainedDPSWeaponSlotAxis, ...]
    candidate_count: int
    denominator_proven: bool
    runtime_evaluation_required: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.slots, tuple):
            raise TypeError("weapon frontier slots must be a tuple")
        if isinstance(self.candidate_count, bool) or not isinstance(self.candidate_count, int):
            raise TypeError("weapon frontier candidate_count must be an integer")
        if self.candidate_count < 0:
            raise ValueError("weapon frontier candidate_count cannot be negative")
        if not isinstance(self.denominator_proven, bool):
            raise TypeError("weapon frontier denominator_proven must be boolean")
        if not isinstance(self.runtime_evaluation_required, bool):
            raise TypeError("weapon frontier runtime_evaluation_required must be boolean")
        if not isinstance(self.evidence, tuple):
            raise TypeError("weapon frontier evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("weapon frontier unresolved must be a tuple")


class ExtremeSustainedDPSWeaponFrontierService:
    """Preserve the modeled weapon trait × canonical enchant-family denominator lazily."""

    def __init__(
        self,
        *,
        enchant_choices: tuple[str, ...],
        trait_choices: tuple[str, ...] | None = None,
    ) -> None:
        self.enchant_choices = self._clean(enchant_choices)
        self.trait_choices = self._clean(
            tuple(trait_choices) if trait_choices is not None else tuple(WEAPON_TRAITS)
        )

    @classmethod
    def from_database(cls, database_path) -> "ExtremeSustainedDPSWeaponFrontierService":
        choices = tuple(
            item for item in BuildEnchantCatalogService(database_path).weapon_choices()
            if str(item or "").strip()
        )
        return cls(enchant_choices=choices)

    def frontier(self, baseline_build: PlayerBuild) -> ExtremeSustainedDPSWeaponFrontier:
        unresolved: list[str] = []
        slots: list[ExtremeSustainedDPSWeaponSlotAxis] = []

        if not self.trait_choices:
            unresolved.append("Canonical weapon trait denominator is empty")
        if not self.enchant_choices:
            unresolved.append("Canonical weapon enchant denominator is empty")

        for field in _WEAPON_FIELDS:
            slot = getattr(baseline_build, field)
            if slot.is_empty:
                continue
            slots.append(
                ExtremeSustainedDPSWeaponSlotAxis(
                    slot=field,
                    trait_choices=self.trait_choices,
                    enchant_choices=self.enchant_choices,
                )
            )

        if not slots:
            unresolved.append("No equipped weapon slots are available for sustained-DPS search")

        count = 1
        for axis in slots:
            count *= axis.choice_count

        proven = bool(slots and count > 0 and not unresolved)
        return ExtremeSustainedDPSWeaponFrontier(
            slots=tuple(slots),
            candidate_count=count,
            denominator_proven=proven,
            runtime_evaluation_required=True,
            evidence=(
                f"Equipped weapon slots in frontier: {len(slots)}",
                f"Modeled weapon traits per equipped slot: {len(self.trait_choices)}",
                f"Canonical weapon enchant families per equipped slot: {len(self.enchant_choices)}",
                f"Lazy weapon trait/enchant denominator: {count}",
                "Weapon enchant identities are enumerated here but proc/cooldown scoring remains runtime-owned",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def candidate_at(
        self,
        baseline_build: PlayerBuild,
        index: int,
    ) -> ExtremeSustainedDPSWeaponCandidate:
        frontier = self.frontier(baseline_build)
        if not frontier.denominator_proven:
            raise ValueError(
                "weapon frontier denominator is unresolved: " + "; ".join(frontier.unresolved)
            )

        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("weapon candidate index must be an integer")
        target = index
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("weapon candidate index out of range")

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

        return ExtremeSustainedDPSWeaponCandidate(
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
    ) -> tuple[ExtremeSustainedDPSWeaponCandidate, ...]:
        frontier = self.frontier(baseline_build)
        start = max(0, int(offset))
        size = max(0, int(limit))
        if size == 0 or start >= frontier.candidate_count:
            return ()
        return tuple(
            self.candidate_at(baseline_build, index)
            for index in range(start, min(frontier.candidate_count, start + size))
        )

    @staticmethod
    def _clean(values: tuple[str, ...]) -> tuple[str, ...]:
        unique = {
            " ".join(str(value or "").strip().split())
            for value in values
            if str(value or "").strip()
        }
        return tuple(sorted(unique, key=str.casefold))


__all__ = [
    "ExtremeSustainedDPSWeaponCandidate",
    "ExtremeSustainedDPSWeaponFrontier",
    "ExtremeSustainedDPSWeaponFrontierService",
    "ExtremeSustainedDPSWeaponSlotAxis",
]
