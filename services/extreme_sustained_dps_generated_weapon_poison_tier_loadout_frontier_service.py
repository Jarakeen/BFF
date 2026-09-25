from __future__ import annotations

"""Finite front/back generated weapon-poison tier loadout frontier."""

from dataclasses import dataclass
from itertools import product

from services.extreme_sustained_dps_generated_weapon_poison_tier_frontier_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate,
    ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService,
)
from services.extreme_sustained_dps_weapon_poison_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonLoadoutCandidate,
    ExtremeSustainedDPSWeaponPoisonSelection,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection:
    poison_id: str
    tier: ExtremeSustainedDPSGeneratedWeaponPoisonTierCandidate | None


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate:
    structural_index: int
    front: ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection
    back: ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontier:
    candidates: tuple[
        ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate,
        ...,
    ]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontierService:
    """Cross source-backed tier choices for the selected front/back poison formulas."""

    def __init__(
        self,
        tier_frontier: ExtremeSustainedDPSGeneratedWeaponPoisonTierFrontierService,
    ) -> None:
        if tier_frontier is None:
            raise ValueError(
                "generated poison tier-loadout frontier requires tier frontier service"
            )
        self.tier_frontier = tier_frontier

    @staticmethod
    def _bar_no_poison() -> tuple[
        ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection,
        ...,
    ]:
        return (
            ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection(
                poison_id="",
                tier=None,
            ),
        )

    def _bar_candidates(
        self,
        selection: ExtremeSustainedDPSWeaponPoisonSelection,
        *,
        bar: str,
    ) -> tuple[
        tuple[ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        poison_id = str(selection.selected_label or "").strip()
        formula = selection.formula
        if not poison_id:
            if formula is not None:
                return (), (), (
                    f"{bar} no-poison selection unexpectedly retains formula provenance",
                )
            return self._bar_no_poison(), (
                f"{bar} poison tier denominator: explicit no-poison",
            ), ()

        if formula is None:
            return (), (), (
                f"{bar} generated poison {poison_id} has no formula provenance",
            )
        if str(formula.canonical_id or "").strip() != poison_id:
            return (), (), (
                f"{bar} generated poison identity does not match formula canonical ID",
            )

        frontier = self.tier_frontier.frontier(formula)
        if not frontier.denominator_proven:
            return (), tuple(frontier.evidence), tuple(frontier.unresolved)
        rows = tuple(
            ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection(
                poison_id=poison_id,
                tier=tier,
            )
            for tier in frontier.candidates
        )
        return rows, tuple(frontier.evidence), ()

    def frontier(
        self,
        poison_loadout: ExtremeSustainedDPSWeaponPoisonLoadoutCandidate,
        *,
        one_bar_only: bool = False,
    ) -> ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontier:
        if poison_loadout is None:
            return ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontier(
                candidates=(),
                candidate_count=0,
                denominator_proven=False,
                unresolved=(
                    "generated poison tier-loadout frontier requires poison formula loadout",
                ),
            )

        front, front_evidence, front_unresolved = self._bar_candidates(
            poison_loadout.front,
            bar="front",
        )
        if one_bar_only:
            back_label = str(poison_loadout.back.selected_label or "").strip()
            if back_label or poison_loadout.back.formula is not None:
                back=()
                back_evidence=()
                back_unresolved=(
                    "one-bar generated poison loadout carries a back-bar poison formula",
                )
            else:
                back=self._bar_no_poison()
                back_evidence=("back poison tier denominator: one-bar no-poison",)
                back_unresolved=()
        else:
            back, back_evidence, back_unresolved = self._bar_candidates(
                poison_loadout.back,
                bar="back",
            )

        unresolved = tuple(
            dict.fromkeys(
                (
                    *front_unresolved,
                    *back_unresolved,
                )
            )
        )
        candidates = tuple(
            ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate(
                structural_index=index,
                front=front_row,
                back=back_row,
            )
            for index, (front_row, back_row) in enumerate(product(front, back))
        )
        if not candidates and not unresolved:
            unresolved = (
                "generated poison tier-loadout denominator is empty",
            )

        return ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontier(
            candidates=candidates,
            candidate_count=len(candidates),
            denominator_proven=bool(candidates) and not unresolved,
            evidence=(
                *front_evidence,
                *back_evidence,
                f"Generated poison tier loadout choices: {len(candidates)}",
                "Front/back poison tier coordinates are searched independently; no preferred solvent/level is assumed.",
            ),
            unresolved=unresolved,
        )

    def candidate_at(
        self,
        poison_loadout: ExtremeSustainedDPSWeaponPoisonLoadoutCandidate,
        *,
        index: int,
        one_bar_only: bool = False,
    ) -> ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate:
        frontier = self.frontier(
            poison_loadout,
            one_bar_only=one_bar_only,
        )
        if not frontier.denominator_proven:
            raise ValueError(
                "generated poison tier-loadout denominator is unresolved: "
                + "; ".join(frontier.unresolved)
            )
        target = int(index)
        if target < 0 or target >= frontier.candidate_count:
            raise IndexError(
                "generated poison tier-loadout candidate index out of range"
            )
        return frontier.candidates[target]


__all__ = [
    "ExtremeSustainedDPSGeneratedWeaponPoisonBarTierSelection",
    "ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate",
    "ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontier",
    "ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutFrontierService",
]
