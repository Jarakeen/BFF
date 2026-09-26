from __future__ import annotations

"""Finite front/back crafted weapon-poison selection frontier for Objective #32."""

from dataclasses import dataclass

from minmax.alchemy_formula_catalog import AlchemyFormula
from minmax.weapon_poison_availability_repository import (
    WeaponPoisonAvailabilityRepository,
)
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonSelection:
    selected_label: str
    formula: AlchemyFormula | None

    @property
    def is_none(self) -> bool:
        return self.formula is None


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonLoadoutCandidate:
    structural_index: int
    front: ExtremeSustainedDPSWeaponPoisonSelection
    back: ExtremeSustainedDPSWeaponPoisonSelection
    build: PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponPoisonFrontier:
    selections: tuple[ExtremeSustainedDPSWeaponPoisonSelection, ...]
    candidate_count: int
    denominator_proven: bool
    one_bar_only: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.selections, tuple):
            raise TypeError("weapon-poison frontier selections must be a tuple")
        if isinstance(self.candidate_count, bool) or not isinstance(self.candidate_count, int):
            raise TypeError("weapon-poison frontier candidate_count must be an integer")
        if self.candidate_count < 0:
            raise ValueError("weapon-poison frontier candidate_count cannot be negative")
        if not isinstance(self.denominator_proven, bool):
            raise TypeError("weapon-poison frontier denominator_proven must be boolean")
        if not isinstance(self.one_bar_only, bool):
            raise TypeError("weapon-poison frontier one_bar_only must be boolean")
        if not isinstance(self.evidence, tuple):
            raise TypeError("weapon-poison frontier evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("weapon-poison frontier unresolved must be a tuple")


class ExtremeSustainedDPSWeaponPoisonFrontierService:
    """Enumerate exact canonical poison formulas independently on front/back bars."""

    def __init__(
        self,
        repository: WeaponPoisonAvailabilityRepository | object,
    ) -> None:
        self.repository = repository

    @classmethod
    def from_database(
        cls,
        database_path,
    ) -> "ExtremeSustainedDPSWeaponPoisonFrontierService":
        return cls(WeaponPoisonAvailabilityRepository(database_path))

    @staticmethod
    def _selection(formula: AlchemyFormula | None) -> ExtremeSustainedDPSWeaponPoisonSelection:
        if formula is None:
            return ExtremeSustainedDPSWeaponPoisonSelection(
                selected_label="",
                formula=None,
            )
        return ExtremeSustainedDPSWeaponPoisonSelection(
            selected_label=str(formula.canonical_id),
            formula=formula,
        )

    def frontier(
        self,
        *,
        one_bar_only: bool = False,
    ) -> ExtremeSustainedDPSWeaponPoisonFrontier:
        if not isinstance(one_bar_only, bool):
            raise TypeError("weapon-poison one_bar_only must be boolean")
        catalog = self.repository.catalog()
        unresolved = list(tuple(getattr(catalog, "unresolved", ()) or ()))
        formulas = tuple(getattr(catalog, "formulas", ()) or ())

        seen: set[str] = set()
        unique_formulas: list[AlchemyFormula] = []
        for formula in formulas:
            identity = str(getattr(formula, "canonical_id", "") or "").strip()
            if not identity:
                unresolved.append(
                    "Canonical poison formula has no stable identity"
                )
                continue
            key = identity.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique_formulas.append(formula)

        selections = (
            self._selection(None),
            *(self._selection(formula) for formula in unique_formulas),
        )
        per_bar = len(selections)
        candidate_count = per_bar if one_bar_only else per_bar * per_bar

        if not unique_formulas and not unresolved:
            unresolved.append(
                "Canonical Poison formula catalog has no selectable formulas"
            )

        final_unresolved = tuple(
            dict.fromkeys(str(row).strip() for row in unresolved if str(row).strip())
        )
        denominator_proven = bool(unique_formulas) and not final_unresolved
        return ExtremeSustainedDPSWeaponPoisonFrontier(
            selections=tuple(selections),
            candidate_count=candidate_count,
            denominator_proven=denominator_proven,
            one_bar_only=one_bar_only,
            evidence=(
                f"Canonical Poison formulas enumerated: {len(unique_formulas)}",
                f"Per-bar poison choices including none: {per_bar}",
                (
                    f"One-bar poison loadouts: {candidate_count}"
                    if one_bar_only
                    else f"Two-bar ordered poison loadouts: {candidate_count}"
                ),
                "Front and back poison ownership are distinct structural choices.",
                "No-poison remains a legal choice on each searched weapon bar.",
                "Poison proc chance, shared cooldown, consequences, and dilution remain runtime-owned.",
            ),
            unresolved=final_unresolved,
        )

    def candidate_at(
        self,
        baseline_build: PlayerBuild,
        *,
        index: int,
        one_bar_only: bool = False,
    ) -> ExtremeSustainedDPSWeaponPoisonLoadoutCandidate:
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("weapon-poison candidate index must be an integer")
        if not isinstance(one_bar_only, bool):
            raise TypeError("weapon-poison one_bar_only must be boolean")
        frontier = self.frontier(one_bar_only=one_bar_only)
        if not frontier.denominator_proven:
            raise ValueError(
                "weapon-poison frontier denominator is unresolved: "
                + "; ".join(frontier.unresolved)
            )
        target = index
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("weapon-poison loadout candidate index out of range")

        count = len(frontier.selections)
        if one_bar_only:
            front_index = target
            back_index = 0
        else:
            front_index, back_index = divmod(target, count)

        front = frontier.selections[front_index]
        back = frontier.selections[back_index]
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        build.FrontBarPoison = front.selected_label
        build.BackBarPoison = "" if one_bar_only else back.selected_label

        return ExtremeSustainedDPSWeaponPoisonLoadoutCandidate(
            structural_index=target,
            front=front,
            back=back,
            build=build,
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonFrontier",
    "ExtremeSustainedDPSWeaponPoisonFrontierService",
    "ExtremeSustainedDPSWeaponPoisonLoadoutCandidate",
    "ExtremeSustainedDPSWeaponPoisonSelection",
]
