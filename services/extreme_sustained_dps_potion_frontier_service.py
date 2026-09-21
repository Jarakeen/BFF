from __future__ import annotations

"""Finite canonical potion-effect-family frontier for generated sustained-DPS search.

Reagent formulas with the same canonical trait set are mechanically equivalent for
selection/activation semantics, so this frontier deduplicates them into one family.
It owns selection identity only. Explicit POTION actions, cooldown, duration, and
Medicinal Use remain runtime responsibilities.
"""

from dataclasses import dataclass

from minmax.potion_availability_repository import PotionAvailabilityRepository
from models.build_model import PlayerBuild


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _slug(value: object) -> str:
    return "_".join(_clean(value).casefold().replace("-", " ").split())


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionFamily:
    selected_label: str
    traits: tuple[str, ...]
    formula_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionCandidate:
    structural_index: int
    family: ExtremeSustainedDPSPotionFamily
    build: PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionFrontier:
    families: tuple[ExtremeSustainedDPSPotionFamily, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSPotionFrontierService:
    """Enumerate canonical potion effect families without assuming activation."""

    def __init__(self, repository: PotionAvailabilityRepository | object) -> None:
        self.repository = repository

    @classmethod
    def from_database(cls, database_path) -> "ExtremeSustainedDPSPotionFrontierService":
        return cls(PotionAvailabilityRepository(database_path))

    @staticmethod
    def _family_label(game_update: object, traits: tuple[str, ...]) -> str:
        update = str(getattr(game_update, "value", game_update) or "").strip().casefold()
        trait_key = "+".join(sorted(_slug(value) for value in traits))
        return f"alchemy_family:{update}:{trait_key}"

    def frontier(self) -> ExtremeSustainedDPSPotionFrontier:
        catalog = self.repository.catalog()
        unresolved = list(getattr(catalog, "unresolved", ()) or ())
        grouped: dict[tuple[str, ...], list[object]] = {}

        for formula in tuple(getattr(catalog, "formulas", ()) or ()):
            traits = tuple(
                sorted(
                    {
                        _clean(value)
                        for value in tuple(getattr(formula, "traits", ()) or ())
                        if _clean(value)
                    },
                    key=str.casefold,
                )
            )
            if not traits:
                unresolved.append(
                    f"Potion formula has no canonical trait family: {getattr(formula, 'canonical_id', '')}"
                )
                continue
            grouped.setdefault(tuple(value.casefold() for value in traits), []).append(formula)

        families: list[ExtremeSustainedDPSPotionFamily] = [
            ExtremeSustainedDPSPotionFamily(
                selected_label="",
                traits=(),
                formula_ids=(),
            )
        ]
        for _key, formulas in sorted(grouped.items()):
            first = formulas[0]
            traits = tuple(
                sorted(
                    {
                        _clean(value)
                        for value in tuple(getattr(first, "traits", ()) or ())
                        if _clean(value)
                    },
                    key=str.casefold,
                )
            )
            family = ExtremeSustainedDPSPotionFamily(
                selected_label=self._family_label(
                    getattr(first, "game_update", getattr(catalog, "game_update", "")),
                    traits,
                ),
                traits=traits,
                formula_ids=tuple(
                    sorted(
                        {
                            str(getattr(formula, "canonical_id", "") or "").strip()
                            for formula in formulas
                            if str(getattr(formula, "canonical_id", "") or "").strip()
                        }
                    )
                ),
            )
            families.append(family)

        if len(families) == 1 and not unresolved:
            unresolved.append("Canonical potion formula catalog has no effect families")

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeSustainedDPSPotionFrontier(
            families=tuple(families),
            candidate_count=len(families),
            denominator_proven=len(families) > 1 and not final_unresolved,
            evidence=(
                f"Canonical reagent formulas reviewed: {len(tuple(getattr(catalog, 'formulas', ()) or ()))}",
                f"Mechanically distinct potion trait families: {max(0, len(families) - 1)}",
                "No-potion selection is retained as a legal identity",
                "Formula reagent permutations sharing one exact trait family are proof-safely deduplicated",
                "Potion activation, cooldown, duration, and Medicinal Use remain runtime-owned",
            ),
            unresolved=final_unresolved,
        )

    def candidate_at(
        self,
        baseline_build: PlayerBuild,
        index: int,
    ) -> ExtremeSustainedDPSPotionCandidate:
        frontier = self.frontier()
        if not frontier.denominator_proven:
            raise ValueError(
                "potion frontier denominator is unresolved: " + "; ".join(frontier.unresolved)
            )
        target = int(index)
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError("potion candidate index out of range")

        family = frontier.families[target]
        build = PlayerBuild.from_dict(baseline_build.to_dict())
        build.Potion = family.selected_label
        return ExtremeSustainedDPSPotionCandidate(
            structural_index=target,
            family=family,
            build=build,
        )

    def page(
        self,
        baseline_build: PlayerBuild,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ExtremeSustainedDPSPotionCandidate, ...]:
        frontier = self.frontier()
        start = max(0, int(offset))
        size = max(0, int(limit))
        if size == 0 or start >= frontier.candidate_count:
            return ()
        return tuple(
            self.candidate_at(baseline_build, index)
            for index in range(start, min(frontier.candidate_count, start + size))
        )


__all__ = [
    "ExtremeSustainedDPSPotionCandidate",
    "ExtremeSustainedDPSPotionFamily",
    "ExtremeSustainedDPSPotionFrontier",
    "ExtremeSustainedDPSPotionFrontierService",
]
