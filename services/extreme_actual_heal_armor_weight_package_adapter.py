from __future__ import annotations

"""Compose H1 gear-package candidates with physical armor-weight legality.

Existing Actual Heal package services remain the owners of set discovery, slot
shape, mythic/monster legality, and package materialization. This adapter adds no
gear math. It takes each concrete package candidate and expands it through the
proof-reduced armor-weight frontier before canonical event scoring.

If canonical armor-type evidence is unresolved for a package, that package is
not silently scored as though its inherited saved-build weights were wearable.
The unresolved boundary is retained for the final H1 result. Diagnostics
accumulate across optimizer passes until ``reset`` so an early proof gap cannot
vanish merely because a later coordinate pass produced fewer candidates.
"""

from dataclasses import dataclass

from minmax.build_candidate import BuildCandidate
from services.extreme_actual_heal_armor_weight_candidate_service import (
    ExtremeActualHealArmorWeightCandidateService,
)


@dataclass(frozen=True)
class ExtremeActualHealArmorWeightPackageAdapterStats:
    raw_package_candidates: int = 0
    expanded_candidates: int = 0
    raw_weight_layouts_reviewed: int = 0
    retained_weight_signatures: int = 0
    unresolved: tuple[str, ...] = ()


class ExtremeActualHealArmorWeightPackageAdapter:
    """Decorate one H1 package candidate service with legal armor-weight expansion."""

    def __init__(
        self,
        delegate,
        armor_weights: ExtremeActualHealArmorWeightCandidateService,
        *,
        label: str,
    ) -> None:
        self.delegate = delegate
        self.armor_weights = armor_weights
        self.label = str(label or delegate.__class__.__name__).strip()
        self._stats = ExtremeActualHealArmorWeightPackageAdapterStats()

    @property
    def stats(self) -> ExtremeActualHealArmorWeightPackageAdapterStats:
        return self._stats

    def reset(self) -> None:
        self._stats = ExtremeActualHealArmorWeightPackageAdapterStats()

    def build_candidates(self, *args, **kwargs) -> tuple[BuildCandidate, ...]:
        raw_candidates = tuple(self.delegate.build_candidates(*args, **kwargs))
        expanded: list[BuildCandidate] = []
        unresolved: list[str] = []
        raw_layouts = 0
        retained_signatures = 0

        for candidate in raw_candidates:
            result = self.armor_weights.expand_candidate(candidate)
            raw_layouts += int(result.raw_layout_count)
            retained_signatures += int(result.retained_signature_count)
            if not result.denominator_proven:
                unresolved.extend(
                    f"{self.label} | {candidate.candidate_id}: {message}"
                    for message in result.unresolved
                )
                continue
            expanded.extend(result.candidates)

        previous = self._stats
        self._stats = ExtremeActualHealArmorWeightPackageAdapterStats(
            raw_package_candidates=(
                previous.raw_package_candidates + len(raw_candidates)
            ),
            expanded_candidates=(
                previous.expanded_candidates + len(expanded)
            ),
            raw_weight_layouts_reviewed=(
                previous.raw_weight_layouts_reviewed + raw_layouts
            ),
            retained_weight_signatures=(
                previous.retained_weight_signatures + retained_signatures
            ),
            unresolved=tuple(
                dict.fromkeys((*previous.unresolved, *unresolved))
            ),
        )
        return tuple(expanded)

    def __getattr__(self, name: str):
        # Preserve specialist helper access used by focused audits/tests while
        # keeping candidate generation routed through this adapter.
        return getattr(self.delegate, name)


__all__ = [
    "ExtremeActualHealArmorWeightPackageAdapter",
    "ExtremeActualHealArmorWeightPackageAdapterStats",
]
