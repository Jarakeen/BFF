from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from minmax.character_build.character_class import CLASS_SKILL_LINES, CharacterClass
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.passive_math import (
    WARDEN_ADVANCED_SPECIES_CRIT_DAMAGE_PER_SLOTTED,
    WARDEN_FLOURISH_RECOVERY_PERCENT,
    WARDEN_FROZEN_ARMOR_RESISTANCE_PER_SLOTTED,
)


_LINE_OWNER: dict[str, CharacterClass] = {
    line: character_class
    for character_class, lines in CLASS_SKILL_LINES.items()
    for line in lines
}


@dataclass(frozen=True)
class ExtremeSubclassSlotAllocationResult:
    objective_key: str
    equipped_skill_lines: tuple[str, ...]
    slot_counts: tuple[tuple[str, int], ...]
    projected_delta: float
    reviewed_sources: tuple[str, ...]


class ExtremeSubclassSlotAllocationService:
    """Optimize reviewed subclass standing effects across one six-slot active bar.

    The service solves only effects whose slot-count mechanics are already
    reviewed in BFF. It deliberately produces a lower bound, not a final class
    route score, because unreviewed skills/passives on the same lines may add
    further value.

    Pressure Points and Expert Mage are class-scoped even though the passives
    live in one class skill line: once the passive's line is equipped, abilities
    from any equipped line of that same class can satisfy the slot count.
    Advanced Species, Flourish, and Frozen Armor are line-scoped.
    """

    ACTIVE_BAR_SLOTS = 6
    NIGHTBLADE_PRESSURE_POINTS_RATING_PER_SLOT = 438.0
    SORCERER_EXPERT_MAGE_POWER_PER_SLOT = 108.0

    @classmethod
    def best_allocation(
        cls,
        equipped_skill_lines: tuple[str, ...],
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> ExtremeSubclassSlotAllocationResult | None:
        lines = tuple(sorted({str(line or "").strip().casefold() for line in equipped_skill_lines if str(line or "").strip()}))
        objective = str(objective_key or "").strip()
        if not lines or not objective:
            return None

        best: ExtremeSubclassSlotAllocationResult | None = None
        # Enumerate every non-negative three-line distribution summing to six.
        for counts in product(range(cls.ACTIVE_BAR_SLOTS + 1), repeat=len(lines)):
            if sum(counts) != cls.ACTIVE_BAR_SLOTS:
                continue
            allocation = dict(zip(lines, counts))
            projected, sources = cls._score_allocation(
                lines,
                allocation,
                objective,
                reference_value=reference_value,
            )
            if projected is None:
                continue
            row = ExtremeSubclassSlotAllocationResult(
                objective_key=objective,
                equipped_skill_lines=lines,
                slot_counts=tuple((line, allocation[line]) for line in lines),
                projected_delta=projected,
                reviewed_sources=sources,
            )
            if best is None or row.projected_delta > best.projected_delta + 1e-9 or (
                abs(row.projected_delta - best.projected_delta) <= 1e-9
                and row.slot_counts < best.slot_counts
            ):
                best = row
        return best

    @classmethod
    def _score_allocation(
        cls,
        lines: tuple[str, ...],
        allocation: dict[str, int],
        objective_key: str,
        *,
        reference_value: float | None,
    ) -> tuple[float | None, tuple[str, ...]]:
        flat = 0.0
        ratio = 0.0
        percent = 0.0
        sources: list[str] = []

        # Pressure Points is owned through Assassination, then counts any
        # Nightblade ability represented on the active bar.
        if "assassination" in lines and objective_key in {"weapon_critical", "spell_critical"}:
            nightblade_slots = sum(
                allocation.get(line, 0)
                for line in lines
                if _LINE_OWNER.get(line) is CharacterClass.NIGHTBLADE
            )
            if nightblade_slots:
                rating = cls.NIGHTBLADE_PRESSURE_POINTS_RATING_PER_SLOT * nightblade_slots
                ratio += GearStatInputResolver.critical_rating_to_ratio(rating)
                sources.append(f"Pressure Points ({nightblade_slots} Nightblade slots)")

        # Expert Mage is owned through Storm Calling, then counts any Sorcerer
        # ability represented on the active bar.
        if "storm_calling" in lines and objective_key in {"weapon_damage", "spell_damage"}:
            sorcerer_slots = sum(
                allocation.get(line, 0)
                for line in lines
                if _LINE_OWNER.get(line) is CharacterClass.SORCERER
            )
            if sorcerer_slots:
                flat += cls.SORCERER_EXPERT_MAGE_POWER_PER_SLOT * sorcerer_slots
                sources.append(f"Expert Mage ({sorcerer_slots} Sorcerer slots)")

        animal_slots = allocation.get("animal_companions", 0)
        if "animal_companions" in lines:
            if objective_key == "critical_damage" and animal_slots:
                ratio += WARDEN_ADVANCED_SPECIES_CRIT_DAMAGE_PER_SLOTTED * animal_slots
                sources.append(f"Advanced Species ({animal_slots} Animal Companions slots)")
            elif objective_key in {"magicka_recovery", "stamina_recovery"} and animal_slots:
                percent += WARDEN_FLOURISH_RECOVERY_PERCENT
                sources.append("Flourish (Animal Companions represented)")

        winter_slots = allocation.get("winters_embrace", 0)
        if "winters_embrace" in lines and objective_key in {"physical_resistance", "spell_resistance"} and winter_slots:
            flat += WARDEN_FROZEN_ARMOR_RESISTANCE_PER_SLOTTED * winter_slots
            sources.append(f"Frozen Armor ({winter_slots} Winter's Embrace slots)")

        if not sources:
            return None, ()
        if percent and reference_value is None:
            return None, ()
        projected = flat + ratio + (float(reference_value) * percent if percent else 0.0)
        return projected, tuple(sources)
