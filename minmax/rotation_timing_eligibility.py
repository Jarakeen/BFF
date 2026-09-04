from __future__ import annotations

from .rotation_action_selection import AbilityActionEligibility
from .rotation_maintenance_readiness import RotationMaintenanceReadiness


def eligibility_from_maintenance_readiness(
    *,
    readiness: RotationMaintenanceReadiness,
    resource_safe: bool = True,
    encounter_allowed: bool = True,
    reason: str | None = None,
) -> AbilityActionEligibility:
    """Build action eligibility from verified maintenance timing readiness.

    Timing comes only from the maintenance-readiness result. Resource and
    encounter legality remain explicit inputs owned by their existing engines.
    This keeps the bridge narrow and prevents timing policy from swallowing
    sustain or mechanic policy.
    """

    candidate = readiness.candidate
    combined_reason_parts = [readiness.reason]
    if reason is not None and str(reason).strip():
        combined_reason_parts.append(str(reason).strip())

    return AbilityActionEligibility(
        bar=candidate.bar,
        slot=candidate.slot,
        skill_name=candidate.skill_name,
        timing_ready=readiness.timing_ready,
        resource_safe=bool(resource_safe),
        encounter_allowed=bool(encounter_allowed),
        reason="; ".join(combined_reason_parts),
    )
