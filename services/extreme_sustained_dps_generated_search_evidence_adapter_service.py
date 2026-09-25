from __future__ import annotations

"""Adapters between sustained-DPS proof/evaluation authorities and branch-and-bound."""

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_runtime_evaluation_service import (
    ExtremeGeneratedSustainedDPSRuntimeResult,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)
from services.extreme_sustained_dps_rotation_upper_bound_service import (
    ExtremeSustainedDPSRotationUpperBound,
)


class ExtremeSustainedDPSGeneratedSearchEvidenceAdapterService:
    """Translate canonical bound/runtime results into search coordinator evidence."""

    @staticmethod
    def branch_bound(
        candidate_key: str,
        rotation_bound: ExtremeSustainedDPSRotationUpperBound,
        *,
        source: str = "canonical sustained-DPS rotation upper bound",
    ) -> ExtremeSustainedDPSBoundEvidence:
        key = str(candidate_key or "").strip()
        if not key:
            raise ValueError("generated search bound adapter requires candidate_key")

        if not isinstance(rotation_bound.proven_safe, bool):
            raise TypeError(
                "generated search bound adapter requires boolean proven_safe"
            )
        return ExtremeSustainedDPSBoundEvidence(
            candidate_key=key,
            upper_bound_dps=rotation_bound.upper_bound_dps,
            proven_safe=rotation_bound.proven_safe,
            source=str(source or "").strip(),
            unresolved=tuple(rotation_bound.unresolved),
        )

    @staticmethod
    def exact_leaf(
        candidate_key: str,
        result: ExtremeGeneratedSustainedDPSRuntimeResult,
    ) -> ExtremeSustainedDPSExactLeafEvaluation:
        key = str(candidate_key or "").strip()
        if not key:
            raise ValueError("generated search exact-leaf adapter requires candidate_key")

        if not isinstance(result.mechanic_complete, bool):
            raise TypeError(
                "generated search exact-leaf adapter requires boolean mechanic_complete"
            )
        record = result.record
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=key,
            modeled_dps=(None if record is None else float(record.modeled_dps)),
            duration_seconds=(
                None if record is None else float(record.duration_seconds)
            ),
            mechanic_complete=result.mechanic_complete,
            evidence=tuple(result.evidence),
            unresolved=tuple(result.unresolved),
        )


__all__ = ["ExtremeSustainedDPSGeneratedSearchEvidenceAdapterService"]
