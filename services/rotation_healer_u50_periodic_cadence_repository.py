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
        ("radiating regeneration", 1): RotationHealerReviewedCadenceEvidence(
            source_name="Radiating Regeneration",
            coefficient_number=1,
            timing=SkillComponentRuntimeTiming(
                interval_seconds=2.0,
                bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
                evidence="target-based Healing over Time effects retain a 2 second frequency",
                source="reviewed_zos_update35_final",
            ),
            provenance=(
                "ZOS PC/Mac Patch Notes v8.1.5: target-based Healing over Time abilities remain at a frequency of 2 seconds",
                "same final Update 35 notes list Regeneration under Restoration Staff Healing over Time adjustments",
                "Radiating Regeneration is the multi-target Regeneration morph and has reviewed PERIODIC component identity",
            ),
        ),
        ("illustrious healing", 1): RotationHealerReviewedCadenceEvidence(
            source_name="Illustrious Healing",
            coefficient_number=1,
            timing=SkillComponentRuntimeTiming(
                interval_seconds=1.0,
                bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
                evidence="static-based Healing over Time effects retain a 1 second frequency",
                source="reviewed_zos_update35_final",
            ),
            provenance=(
                "ZOS PC/Mac Patch Notes v8.1.5: static-based Healing over Time abilities remain at a frequency of 1 second",
                "same final Update 35 notes list Grand Healing and its morphs as static-area Healing over Time abilities",
                "Illustrious Healing remains the duration-extending Grand Healing morph",
                "current U50 ability duration is resolved separately from canonical ability.duration evidence",
            ),
        ),
        ("echoing vigor", 1): RotationHealerReviewedCadenceEvidence(
            source_name="Echoing Vigor",
            coefficient_number=1,
            timing=SkillComponentRuntimeTiming(
                interval_seconds=2.0,
                bound_kind=RuntimeCadenceBoundKind.CALLER_ACTIVE_WINDOW,
                evidence="target-based Healing over Time effects retain a 2 second frequency",
                source="reviewed_zos_update35_final",
            ),
            provenance=(
                "ZOS PC/Mac Patch Notes v8.1.5: target-based Healing over Time abilities remain at a frequency of 2 seconds",
                "same final Update 35 notes list Vigor and Echoing Vigor under Healing over Time adjustments",
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
