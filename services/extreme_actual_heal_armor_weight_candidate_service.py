from __future__ import annotations

"""Build proof-reduced physical armor-weight candidates for standing H1.

The raw per-slot armor-weight product can contain up to 3^7 layouts. For the
currently reviewed standing MOST Actual Heal mechanics, armor weight can change
the event through Medium Armor piece-count passives and through the number of
distinct armor types used by Undaunted Mettle. Set identity and exact slot
legality remain fixed by the supplied build.

Accordingly this service enumerates every physically legal slot-weight layout,
then preserves one deterministic concrete witness for each
``(medium_piece_count, distinct_armor_type_count)`` signature. Canonical build
math still performs the actual score; this service owns legality and safe state
reduction only.
"""

from dataclasses import dataclass
from itertools import product

from minmax.build_candidate import BuildCandidate, BuildChange
from models.build_model import ARMOR_SLOTS, PlayerBuild
from services.extreme_actual_heal_armor_weight_legality_service import (
    ExtremeActualHealArmorWeightLegalityService,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService


@dataclass(frozen=True)
class ExtremeActualHealArmorWeightCandidateResult:
    candidates: tuple[BuildCandidate, ...]
    raw_layout_count: int
    retained_signature_count: int
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()


class ExtremeActualHealArmorWeightCandidateService:
    """Enumerate legal H1 armor-weight layouts and retain proof-safe witnesses."""

    def __init__(self, legality: ExtremeActualHealArmorWeightLegalityService) -> None:
        self.legality = legality

    @staticmethod
    def _weights(build: PlayerBuild) -> tuple[str, ...]:
        return tuple(
            str(build.Armor[slot].get("Weight", "") or "").strip().title()
            for slot in ARMOR_SLOTS
        )

    @staticmethod
    def _signature(weights: tuple[str, ...]) -> tuple[int, int]:
        return (
            sum(1 for weight in weights if weight == "Medium"),
            len(set(weights)),
        )

    def _witnesses(
        self,
        build: PlayerBuild,
    ) -> tuple[dict[tuple[int, int], tuple[str, ...]], int, tuple[str, ...]]:
        evidence = self.legality.evaluate(build)
        unresolved = tuple(
            dict.fromkeys(
                problem
                for row in evidence.slots
                for problem in row.unresolved
                if str(problem or "").strip()
            )
        )
        if unresolved:
            return {}, 0, unresolved

        options = tuple(row.allowed_weights for row in evidence.slots)
        if len(options) != len(ARMOR_SLOTS) or any(not values for values in options):
            return {}, 0, (
                "H1 armor-weight legality did not provide a non-empty option set for every armor slot",
            )

        witnesses: dict[tuple[int, int], tuple[str, ...]] = {}
        raw = 0
        for raw_weights in product(*options):
            raw += 1
            weights = tuple(str(value).title() for value in raw_weights)
            signature = self._signature(weights)
            incumbent = witnesses.get(signature)
            if incumbent is None or weights < incumbent:
                witnesses[signature] = weights
        return witnesses, raw, ()

    @staticmethod
    def _materialize(build: PlayerBuild, weights: tuple[str, ...]) -> PlayerBuild:
        candidate = PlayerBuild.from_dict(build.to_dict())
        if len(weights) != len(ARMOR_SLOTS):
            raise ValueError("H1 armor-weight witness does not cover every armor slot")
        for slot, weight in zip(ARMOR_SLOTS, weights):
            candidate.Armor[slot]["Weight"] = weight
        return candidate

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
    ) -> ExtremeActualHealArmorWeightCandidateResult:
        witnesses, raw, unresolved = self._witnesses(baseline_build)
        if unresolved:
            return ExtremeActualHealArmorWeightCandidateResult(
                candidates=(),
                raw_layout_count=raw,
                retained_signature_count=0,
                denominator_proven=False,
                unresolved=unresolved,
            )

        before_weights = self._weights(baseline_build)
        result: list[BuildCandidate] = []
        for signature in sorted(witnesses):
            weights = witnesses[signature]
            if weights == before_weights:
                continue
            build = self._materialize(baseline_build, weights)
            medium_count, type_count = signature
            result.append(
                ExtremeCompleteOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"actual-heal-armor-weight:m{medium_count}:t{type_count}",
                    path="Armor.WeightComposition",
                    before=dict(zip(ARMOR_SLOTS, before_weights)),
                    after={
                        "weights": dict(zip(ARMOR_SLOTS, weights)),
                        "medium_piece_count": medium_count,
                        "distinct_armor_type_count": type_count,
                    },
                    source="extreme:actual-heal:armor-weight-frontier",
                )
            )

        return ExtremeActualHealArmorWeightCandidateResult(
            candidates=tuple(result),
            raw_layout_count=raw,
            retained_signature_count=len(witnesses),
            denominator_proven=bool(witnesses),
        )

    def expand_candidate(
        self,
        candidate: BuildCandidate,
    ) -> ExtremeActualHealArmorWeightCandidateResult:
        build = candidate.candidate_build
        witnesses, raw, unresolved = self._witnesses(build)
        if unresolved:
            return ExtremeActualHealArmorWeightCandidateResult(
                candidates=(),
                raw_layout_count=raw,
                retained_signature_count=0,
                denominator_proven=False,
                unresolved=unresolved,
            )

        before_weights = self._weights(build)
        variants: list[BuildCandidate] = []
        for signature in sorted(witnesses):
            weights = witnesses[signature]
            if weights == before_weights:
                variants.append(candidate)
                continue
            medium_count, type_count = signature
            materialized = self._materialize(build, weights)
            change = BuildChange.from_values(
                path="Armor.WeightComposition",
                before=dict(zip(ARMOR_SLOTS, before_weights)),
                after={
                    "weights": dict(zip(ARMOR_SLOTS, weights)),
                    "medium_piece_count": medium_count,
                    "distinct_armor_type_count": type_count,
                },
                source="extreme:actual-heal:armor-weight-frontier",
            )
            variants.append(
                BuildCandidate.from_build(
                    character_id=candidate.character_id,
                    baseline_build_id=candidate.baseline_build_id,
                    candidate_id=(
                        f"{candidate.candidate_id}:armor-weight:m{medium_count}:t{type_count}"
                    ),
                    candidate_build=materialized,
                    changes=(*candidate.changes, change),
                    candidate_source=f"{candidate.candidate_source}:armor-weight-frontier",
                )
            )

        return ExtremeActualHealArmorWeightCandidateResult(
            candidates=tuple(variants),
            raw_layout_count=raw,
            retained_signature_count=len(witnesses),
            denominator_proven=bool(witnesses),
        )


__all__ = [
    "ExtremeActualHealArmorWeightCandidateResult",
    "ExtremeActualHealArmorWeightCandidateService",
]
