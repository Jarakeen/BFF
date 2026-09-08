from __future__ import annotations

from dataclasses import dataclass

from minmax.skill_component_runtime_timing import (
    RuntimeCadenceBoundKind,
    SkillComponentRuntimeTiming,
)


@dataclass(frozen=True)
class RotationHealerReviewedCadenceEvidence:
    source_name: str
    coefficient_number: int
    timing: SkillComponentRuntimeTiming
    provenance: tuple[str, ...]


class RotationHealerU50PeriodicCadenceRepository:
    """Reviewed U50 cadence evidence not preserved by local coefficient text.

    This repository is deliberately tiny and exact-name/component scoped. It does
    not infer cadence from total duration, total healing, morph family, or generic
    HoT expectations. Entries exist only where reviewed source evidence states the
    recurring interval explicitly enough to bind the current U50 component.

    First-tick placement, expiry-boundary semantics, and refresh/recast behavior
    remain separate runtime facts and are not supplied here.
    """

    _REVIEWED: dict[tuple[str, int], RotationHealerReviewedCadenceEvidence] = {
        ("illustrious healing", 1): RotationHealerReviewedCadenceEvidence(
            source_name="Illustrious Healing",
            coefficient_number=1,
            timing=SkillComponentRuntimeTiming(
                interval_seconds=2.0,
                bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
                evidence="Grand Healing and its morphs heal once every 2 seconds",
                source="reviewed_zos_patch_history_u50",
            ),
            provenance=(
                "ZOS PTS Patch Notes v8.1.0: Grand Healing and its morphs heal once every 2 seconds over 10 seconds",
                "same patch: Illustrious Healing remains the duration-extending Grand Healing morph",
                "current U50 ability duration is resolved separately from canonical ability.duration evidence",
            ),
        ),
        ("echoing vigor", 1): RotationHealerReviewedCadenceEvidence(
            source_name="Echoing Vigor",
            coefficient_number=1,
            timing=SkillComponentRuntimeTiming(
                interval_seconds=2.0,
                bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
                evidence="Vigor tick frequency changed to once every 2 seconds",
                source="reviewed_zos_patch_history_u50",
            ),
            provenance=(
                "ZOS PTS Patch Notes v5.1.0: Vigor tick frequency decreased to 2 seconds from 1 second",
                "same patch: Echoing Vigor reintroduces the area-of-effect healing capability without a separate cadence override",
                "current U50 Echoing Vigor duration is resolved separately from canonical ability.duration evidence",
            ),
        ),
    }

    def get(
        self,
        *,
        source_name: str,
        coefficient_number: int,
    ) -> RotationHealerReviewedCadenceEvidence | None:
        key = (str(source_name or "").strip().casefold(), int(coefficient_number))
        return self._REVIEWED.get(key)
