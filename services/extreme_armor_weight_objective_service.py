from __future__ import annotations

"""Project reviewed armor-weight passive formulas into Extreme objective units.

Armor passive mechanics remain owned by ``minmax.passive_math`` and the shared
armor input resolver. This service only enumerates legal seven-piece
Light/Medium/Heavy compositions and projects the currently reviewed standing
passives into the objective units already used by the Extreme engine.

The service deliberately does not model armor traits, glyphs, base armor values,
Undaunted Mettle, or runtime block/sustain consequences. Those stay separate
source families/contexts rather than being smuggled into one armor score.
"""

from dataclasses import dataclass

from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.passive_math import (
    heavy_armor_resolve_resistance,
    light_armor_critical_rating,
    light_armor_magicka_recovery_percent,
    light_armor_spell_resistance,
    medium_armor_crit_damage_healing_percent,
    medium_armor_stamina_recovery_percent,
    medium_armor_weapon_spell_damage_percent,
)


@dataclass(frozen=True)
class ExtremeArmorWeightObjectiveCandidate:
    objective_key: str
    light_pieces: int
    medium_pieces: int
    heavy_pieces: int
    flat: float = 0.0
    ratio: float = 0.0
    percent_of_reference: float = 0.0
    projected_delta: float | None = None
    sources: tuple[str, ...] = ()

    @property
    def composition_label(self) -> str:
        return f"{self.light_pieces}L/{self.medium_pieces}M/{self.heavy_pieces}H"


class ExtremeArmorWeightObjectiveService:
    """Enumerate reviewed max-rank armor-weight passive contributions."""

    ARMOR_SLOTS = 7
    REVIEWED_OBJECTIVES = (
        "critical_damage",
        "magicka_recovery",
        "stamina_recovery",
        "physical_resistance",
        "spell_resistance",
        "spell_damage",
        "weapon_damage",
        "spell_critical",
        "weapon_critical",
    )

    @classmethod
    def legal_compositions(cls) -> tuple[tuple[int, int, int], ...]:
        rows: list[tuple[int, int, int]] = []
        for light in range(cls.ARMOR_SLOTS + 1):
            for medium in range(cls.ARMOR_SLOTS - light + 1):
                heavy = cls.ARMOR_SLOTS - light - medium
                rows.append((light, medium, heavy))
        return tuple(rows)

    @staticmethod
    def _projected_delta(
        *,
        flat: float,
        ratio: float,
        percent_of_reference: float,
        reference_value: float | None,
    ) -> float | None:
        if percent_of_reference and reference_value is None:
            return None
        reference = 0.0 if reference_value is None else float(reference_value)
        return float(flat) + float(ratio) + (reference * float(percent_of_reference))

    @classmethod
    def candidate_for_composition(
        cls,
        objective_key: str,
        *,
        light_pieces: int,
        medium_pieces: int,
        heavy_pieces: int,
        reference_value: float | None = None,
    ) -> ExtremeArmorWeightObjectiveCandidate:
        objective = objective_key.strip().casefold()
        if objective not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme armor objective: {objective_key!r}")

        counts = (int(light_pieces), int(medium_pieces), int(heavy_pieces))
        if any(count < 0 for count in counts) or sum(counts) != cls.ARMOR_SLOTS:
            raise ValueError("Extreme armor composition must contain exactly seven non-negative pieces")

        light, medium, heavy = counts
        flat = ratio = percent = 0.0
        sources: list[str] = []

        if objective == "magicka_recovery" and light:
            percent += light_armor_magicka_recovery_percent(light)
            sources.append(f"Light Armor: Evocation ({light} pieces)")
        elif objective == "spell_resistance" and light:
            flat += light_armor_spell_resistance(light)
            sources.append(f"Light Armor: Spell Warding ({light} pieces)")
        elif objective in {"spell_critical", "weapon_critical"} and light:
            rating = light_armor_critical_rating(light)
            ratio += GearStatInputResolver.critical_rating_to_ratio(rating)
            sources.append(f"Light Armor: Prodigy ({light} pieces)")

        if objective == "stamina_recovery" and medium:
            percent += medium_armor_stamina_recovery_percent(medium)
            sources.append(f"Medium Armor: Wind Walker ({medium} pieces)")
        elif objective in {"spell_damage", "weapon_damage"} and medium:
            percent += medium_armor_weapon_spell_damage_percent(medium)
            sources.append(f"Medium Armor: Agility ({medium} pieces)")
        elif objective == "critical_damage" and medium:
            ratio += medium_armor_crit_damage_healing_percent(medium)
            sources.append(f"Medium Armor: Dexterity ({medium} pieces)")

        if objective in {"physical_resistance", "spell_resistance"} and heavy:
            flat += heavy_armor_resolve_resistance(heavy)
            sources.append(f"Heavy Armor: Resolve ({heavy} pieces)")

        return ExtremeArmorWeightObjectiveCandidate(
            objective_key=objective,
            light_pieces=light,
            medium_pieces=medium,
            heavy_pieces=heavy,
            flat=flat,
            ratio=ratio,
            percent_of_reference=percent,
            projected_delta=cls._projected_delta(
                flat=flat,
                ratio=ratio,
                percent_of_reference=percent,
                reference_value=reference_value,
            ),
            sources=tuple(sources),
        )

    @classmethod
    def candidates_for_objective(
        cls,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> tuple[ExtremeArmorWeightObjectiveCandidate, ...]:
        rows = tuple(
            cls.candidate_for_composition(
                objective_key,
                light_pieces=light,
                medium_pieces=medium,
                heavy_pieces=heavy,
                reference_value=reference_value,
            )
            for light, medium, heavy in cls.legal_compositions()
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.projected_delta is None,
                    -(row.projected_delta or 0.0),
                    -row.light_pieces,
                    -row.medium_pieces,
                    -row.heavy_pieces,
                ),
            )
        )

    @classmethod
    def best_for_objective(
        cls,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> ExtremeArmorWeightObjectiveCandidate | None:
        return next(
            (
                row
                for row in cls.candidates_for_objective(
                    objective_key,
                    reference_value=reference_value,
                )
                if row.projected_delta is not None
            ),
            None,
        )
