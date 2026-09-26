from __future__ import annotations

"""Lazy legal armor trait/enchant frontier for sustained-DPS generated search.

This service preserves the complete modeled armor trait/enchant denominator for the
actually equipped armor slots on one concrete build witness. It does not score DPS,
does not reduce states by max-resource assumptions, and never materializes the full
Cartesian product in memory.

Armor enchant variation is enabled only on slots whose canonical static resolver
boundary is already CP160 + Truly Superb. Other equipped slots still enumerate the
modeled trait axis while retaining their existing enchant unchanged.
"""

from dataclasses import dataclass

from minmax.build_candidate_armor_enchant import MODELED_ARMOR_ENCHANTS
from minmax.build_candidate_armor_trait import MODELED_ARMOR_TRAITS
from models.build_model import ARMOR_SLOTS, PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSArmorSlotAxis:
    slot: str
    trait_choices: tuple[str, ...]
    enchant_choices: tuple[str, ...]
    enchant_axis_active: bool

    @property
    def choice_count(self) -> int:
        return len(self.trait_choices) * len(self.enchant_choices)


@dataclass(frozen=True)
class ExtremeSustainedDPSArmorTraitEnchantCandidate:
    structural_index: int
    slot_choices: tuple[tuple[str, str, str], ...]
    build: PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSArmorTraitEnchantFrontier:
    slots: tuple[ExtremeSustainedDPSArmorSlotAxis, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.slots, tuple):
            raise TypeError("armor trait/enchant frontier slots must be a tuple")
        if isinstance(self.candidate_count, bool) or not isinstance(self.candidate_count, int):
            raise TypeError("armor trait/enchant frontier candidate_count must be an integer")
        if self.candidate_count < 0:
            raise ValueError("armor trait/enchant frontier candidate_count cannot be negative")
        if not isinstance(self.denominator_proven, bool):
            raise TypeError("armor trait/enchant frontier denominator_proven must be boolean")
        if not isinstance(self.evidence, tuple):
            raise TypeError("armor trait/enchant frontier evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("armor trait/enchant frontier unresolved must be a tuple")


class ExtremeSustainedDPSArmorTraitEnchantFrontierService:
    """Count and page the complete modeled armor trait/enchant product lazily."""

    @classmethod
    def frontier(
        cls,
        baseline_build: PlayerBuild,
    ) -> ExtremeSustainedDPSArmorTraitEnchantFrontier:
        slots: list[ExtremeSustainedDPSArmorSlotAxis] = []
        unresolved: list[str] = []

        for slot in ARMOR_SLOTS:
            entry = baseline_build.Armor.get(slot, {})
            if not cls._equipped(entry):
                continue

            current_enchant = str(entry.get("Enchant", "") or "").strip()
            enchant_axis_active = cls._enchant_axis_active(entry)
            enchant_choices = (
                tuple(MODELED_ARMOR_ENCHANTS)
                if enchant_axis_active
                else (current_enchant,)
            )
            if not enchant_choices:
                enchant_choices = ("",)

            slots.append(
                ExtremeSustainedDPSArmorSlotAxis(
                    slot=slot,
                    trait_choices=tuple(MODELED_ARMOR_TRAITS),
                    enchant_choices=tuple(enchant_choices),
                    enchant_axis_active=enchant_axis_active,
                )
            )

        if not slots:
            unresolved.append("No equipped armor slots are available for trait/enchant search")

        count = 1
        for axis in slots:
            if not axis.trait_choices or not axis.enchant_choices:
                unresolved.append(f"{axis.slot}: armor trait/enchant axis has no legal choices")
                count = 0
                break
            count *= axis.choice_count

        proven = bool(slots and count > 0 and not unresolved)
        evidence = (
            f"Equipped armor slots in frontier: {len(slots)}",
            f"Modeled armor traits per equipped slot: {len(MODELED_ARMOR_TRAITS)}",
            f"Modeled armor enchants on eligible CP160/Truly Superb slots: {len(MODELED_ARMOR_ENCHANTS)}",
            f"Lazy armor trait/enchant denominator: {count}",
            "Frontier preserves the full modeled product; no DPS-specific dominance reduction is assumed",
        )
        return ExtremeSustainedDPSArmorTraitEnchantFrontier(
            slots=tuple(slots),
            candidate_count=count,
            denominator_proven=proven,
            evidence=evidence,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @classmethod
    def candidate_at(
        cls,
        baseline_build: PlayerBuild,
        index: int,
    ) -> ExtremeSustainedDPSArmorTraitEnchantCandidate:
        frontier = cls.frontier(baseline_build)
        if not frontier.denominator_proven:
            raise ValueError(
                "armor trait/enchant frontier denominator is unresolved: "
                + "; ".join(frontier.unresolved)
            )

        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("armor trait/enchant candidate index must be an integer")
        target = index
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("armor trait/enchant candidate index out of range")

        remainder = target
        selected_reversed: list[tuple[str, str, str]] = []
        for axis in reversed(frontier.slots):
            local_count = axis.choice_count
            local_index = remainder % local_count
            remainder //= local_count

            enchant_count = len(axis.enchant_choices)
            trait_index = local_index // enchant_count
            enchant_index = local_index % enchant_count
            selected_reversed.append(
                (
                    axis.slot,
                    axis.trait_choices[trait_index],
                    axis.enchant_choices[enchant_index],
                )
            )

        selected = tuple(reversed(selected_reversed))
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        for slot, trait, enchant in selected:
            entry = build.Armor[slot]
            entry["Trait"] = trait
            entry["Quality"] = "Gold"
            entry["Enchant"] = enchant
            if cls._enchant_axis_active(entry) or enchant in MODELED_ARMOR_ENCHANTS:
                entry["Level"] = "CP160"
                entry["EnchantTier"] = "Truly Superb"

        return ExtremeSustainedDPSArmorTraitEnchantCandidate(
            structural_index=target,
            slot_choices=selected,
            build=build,
        )

    @classmethod
    def page(
        cls,
        baseline_build: PlayerBuild,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ExtremeSustainedDPSArmorTraitEnchantCandidate, ...]:
        frontier = cls.frontier(baseline_build)
        if isinstance(offset, bool) or not isinstance(offset, int):
            raise TypeError("armor trait/enchant page offset must be an integer")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("armor trait/enchant page limit must be an integer")
        start = max(0, offset)
        size = max(0, limit)
        if size == 0 or start >= frontier.candidate_count:
            return ()
        stop = min(frontier.candidate_count, start + size)
        return tuple(
            cls.candidate_at(baseline_build, index)
            for index in range(start, stop)
        )

    @staticmethod
    def _equipped(entry: dict[str, str]) -> bool:
        return bool(
            str(entry.get("Set", "") or "").strip()
            or str(entry.get("Set2", "") or "").strip()
            or str(entry.get("Weight", "") or "").strip()
        )

    @staticmethod
    def _enchant_axis_active(entry: dict[str, str]) -> bool:
        return (
            str(entry.get("Level", "") or "").strip().casefold() == "cp160"
            and str(entry.get("EnchantTier", "") or "").strip().casefold()
            == "truly superb"
        )


__all__ = [
    "ExtremeSustainedDPSArmorSlotAxis",
    "ExtremeSustainedDPSArmorTraitEnchantCandidate",
    "ExtremeSustainedDPSArmorTraitEnchantFrontier",
    "ExtremeSustainedDPSArmorTraitEnchantFrontierService",
]
