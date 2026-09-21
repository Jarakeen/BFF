from __future__ import annotations

"""Adapt reviewed Mundus × provisioning dominance into canonical search proof evidence."""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_mundus_provisioning_dominance_service import (
    ExtremeSustainedDPSMundusProvisioningDominanceResult,
)
from services.extreme_sustained_dps_structural_action_upper_bound_service import (
    ExtremeSustainedDPSAbsoluteActionDamageCeiling,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSMundusProvisioningProofAdapterResult:
    axis_coverage: ExtremeSustainedDPSAxisCoverageProof
    action_ceiling: ExtremeSustainedDPSAbsoluteActionDamageCeiling
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSMundusProvisioningProofAdapterService:
    """Promote only a complete joint finite-grid result into canonical proof forms."""

    @classmethod
    def adapt(
        cls,
        result: ExtremeSustainedDPSMundusProvisioningDominanceResult,
    ) -> ExtremeSustainedDPSMundusProvisioningProofAdapterResult:
        unresolved = list(result.unresolved)

        complete = (
            result.expected_combinations > 0
            and result.evaluated_combinations == result.expected_combinations
            and result.resolved_combinations == result.expected_combinations
            and result.upper_bound_damage is not None
            and result.dominance.complete
            and not unresolved
        )

        axis_coverage = ExtremeSustainedDPSAxisCoverageProof(
            source="canonical joint Mundus × provisioning dominance",
            dominated_axes=("mundus", "food") if complete else (),
            unresolved=tuple(unresolved),
        )
        action_ceiling = ExtremeSustainedDPSAbsoluteActionDamageCeiling(
            upper_bound_damage=(
                float(result.upper_bound_damage)
                if complete and result.upper_bound_damage is not None
                else None
            ),
            proven_safe=complete,
            covers_periodic_and_triggered=complete,
            source="canonical joint Mundus × provisioning finite action grid",
            unresolved=tuple(unresolved),
        )

        return ExtremeSustainedDPSMundusProvisioningProofAdapterResult(
            axis_coverage=axis_coverage,
            action_ceiling=action_ceiling,
            evidence=(
                f"Joint combinations expected/evaluated/resolved: "
                f"{result.expected_combinations}/"
                f"{result.evaluated_combinations}/"
                f"{result.resolved_combinations}",
                (
                    "Canonical mutation-axis coverage promoted: mundus + food"
                    if complete
                    else "Canonical mutation-axis coverage withheld"
                ),
                (
                    f"Joint finite-grid absolute action ceiling: "
                    f"{float(result.upper_bound_damage):g}"
                    if complete and result.upper_bound_damage is not None
                    else "Joint finite-grid absolute action ceiling: unavailable"
                ),
                "Coupled Mundus/provisioning dominance is preserved as one joint proof",
            ),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "ExtremeSustainedDPSMundusProvisioningProofAdapterResult",
    "ExtremeSustainedDPSMundusProvisioningProofAdapterService",
]
