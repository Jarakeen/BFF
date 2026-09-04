from __future__ import annotations

from dataclasses import dataclass
import math

from .saved_build_maintenance_candidates import SavedBuildMaintenanceCandidate


@dataclass(frozen=True)
class RotationMaintenanceReadiness:
    """Evidence-backed readiness for one maintenance ability at one decision time."""

    candidate: SavedBuildMaintenanceCandidate
    decision_time_seconds: float
    last_cast_time_seconds: float | None
    refresh_lead_seconds: float
    expires_at_seconds: float | None
    ready_at_seconds: float
    timing_ready: bool
    reason: str


def assess_rotation_maintenance_readiness(
    *,
    candidate: SavedBuildMaintenanceCandidate,
    decision_time_seconds: float,
    last_cast_time_seconds: float | None,
    refresh_lead_seconds: float = 0.0,
) -> RotationMaintenanceReadiness:
    """Assess whether a duration-backed maintenance skill is due for refresh.

    The canonical duration comes from ``SavedBuildMaintenanceCandidate``. The
    caller owns refresh policy through ``refresh_lead_seconds`` and owns cast
    history through ``last_cast_time_seconds``. This layer does not infer either.

    A skill with no known prior cast is considered ready for its initial cast.
    Otherwise it becomes ready at ``last_cast + duration - refresh_lead``.
    """

    decision_time = float(decision_time_seconds)
    if not math.isfinite(decision_time) or decision_time < 0:
        raise ValueError("maintenance decision time must be finite and non-negative")

    refresh_lead = float(refresh_lead_seconds)
    if not math.isfinite(refresh_lead) or refresh_lead < 0:
        raise ValueError("maintenance refresh lead must be finite and non-negative")
    if refresh_lead > candidate.duration_seconds:
        raise ValueError("maintenance refresh lead cannot exceed canonical duration")

    if last_cast_time_seconds is None:
        return RotationMaintenanceReadiness(
            candidate=candidate,
            decision_time_seconds=decision_time,
            last_cast_time_seconds=None,
            refresh_lead_seconds=refresh_lead,
            expires_at_seconds=None,
            ready_at_seconds=decision_time,
            timing_ready=True,
            reason="no prior cast is known; initial maintenance cast is ready",
        )

    last_cast = float(last_cast_time_seconds)
    if not math.isfinite(last_cast) or last_cast < 0:
        raise ValueError("maintenance last-cast time must be finite and non-negative")
    if last_cast > decision_time:
        raise ValueError("maintenance last-cast time cannot be after decision time")

    expires_at = last_cast + float(candidate.duration_seconds)
    ready_at = expires_at - refresh_lead
    timing_ready = decision_time >= ready_at

    return RotationMaintenanceReadiness(
        candidate=candidate,
        decision_time_seconds=decision_time,
        last_cast_time_seconds=last_cast,
        refresh_lead_seconds=refresh_lead,
        expires_at_seconds=expires_at,
        ready_at_seconds=ready_at,
        timing_ready=timing_ready,
        reason=(
            "maintenance refresh window is open"
            if timing_ready
            else "canonical effect duration is still active before the refresh window"
        ),
    )
