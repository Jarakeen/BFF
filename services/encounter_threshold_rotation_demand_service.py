from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
    EncounterThresholdClockPoint,
)


@dataclass(frozen=True)
class EncounterThresholdRotationDemandPolicy:
    """Explicit role policy for one projected health-threshold clock point."""

    fact_key: str
    threshold_fraction: float
    kind: RotationDemandKind
    pattern: RotationDemandPattern
    lead_seconds: float = 0.0
    window_seconds: float = 1.0
    target_count: int = 1
    name: str = ""

    def __post_init__(self) -> None:
        key = str(self.fact_key or "").strip()
        if not key:
            raise ValueError("threshold rotation demand policy requires fact_key")
        object.__setattr__(self, "fact_key", key)

        threshold = float(self.threshold_fraction)
        if not math.isfinite(threshold) or not 0 < threshold < 1:
            raise ValueError("threshold_fraction must be finite and between 0 and 1")
        object.__setattr__(self, "threshold_fraction", threshold)

        if not isinstance(self.kind, RotationDemandKind):
            object.__setattr__(self, "kind", RotationDemandKind(str(self.kind)))
        if not isinstance(self.pattern, RotationDemandPattern):
            object.__setattr__(self, "pattern", RotationDemandPattern(str(self.pattern)))

        lead = float(self.lead_seconds)
        width = float(self.window_seconds)
        if not math.isfinite(lead) or lead < 0:
            raise ValueError("lead_seconds must be finite and non-negative")
        if not math.isfinite(width) or width <= 0:
            raise ValueError("window_seconds must be finite and positive")
        object.__setattr__(self, "lead_seconds", lead)
        object.__setattr__(self, "window_seconds", width)

        count = int(self.target_count)
        if count <= 0:
            raise ValueError("target_count must be positive")
        object.__setattr__(self, "target_count", count)
        object.__setattr__(self, "name", str(self.name or "").strip())


@dataclass(frozen=True)
class EncounterThresholdRotationDemandProjection:
    encounter_id: str
    demands: tuple[RotationDemandWindow, ...]
    unresolved: tuple[str, ...]


def _matches(
    point: EncounterThresholdClockPoint,
    policy: EncounterThresholdRotationDemandPolicy,
) -> bool:
    return (
        point.fact_key == policy.fact_key
        and math.isclose(
            float(point.threshold_fraction),
            float(policy.threshold_fraction),
            rel_tol=0.0,
            abs_tol=1e-9,
        )
    )


class EncounterThresholdRotationDemandService:
    """Convert projected health thresholds into explicit role preparation windows.

    The encounter projection owns when a health threshold is expected under a
    supplied raid-damage trajectory. The policy owns what the role should prepare
    for and how early. Missing or unresolved clock projections remain unresolved.
    """

    def project(
        self,
        *,
        thresholds: EncounterHealthThresholdProjection,
        policies: tuple[EncounterThresholdRotationDemandPolicy, ...],
    ) -> EncounterThresholdRotationDemandProjection:
        seen: set[tuple[str, float]] = set()
        demands: list[RotationDemandWindow] = []
        unresolved: list[str] = []

        for policy in policies:
            key = (policy.fact_key, policy.threshold_fraction)
            if key in seen:
                raise ValueError(
                    "duplicate threshold rotation demand policy for "
                    f"{policy.fact_key} at {policy.threshold_fraction * 100:g}%"
                )
            seen.add(key)

            matches = [point for point in thresholds.points if _matches(point, policy)]
            if not matches:
                unresolved.append(
                    f"{policy.fact_key} at {policy.threshold_fraction * 100:g}%: "
                    "no projected canonical threshold point is available"
                )
                continue
            if len(matches) > 1:
                raise ValueError(
                    "multiple projected threshold points match policy for "
                    f"{policy.fact_key} at {policy.threshold_fraction * 100:g}%"
                )

            point = matches[0]
            if not point.resolved or point.time_seconds is None:
                unresolved.append(
                    f"{policy.fact_key} at {policy.threshold_fraction * 100:g}%: "
                    f"clock projection unresolved ({point.reason or 'unknown reason'})"
                )
                continue

            event_time = float(point.time_seconds)
            start = max(0.0, event_time - policy.lead_seconds)
            end = event_time + policy.window_seconds
            demands.append(
                RotationDemandWindow(
                    name=policy.name or point.label,
                    start_seconds=start,
                    end_seconds=end,
                    kind=policy.kind,
                    pattern=policy.pattern,
                    target_count=policy.target_count,
                )
            )

        demands.sort(key=lambda row: (row.start_seconds, row.end_seconds, row.name))
        return EncounterThresholdRotationDemandProjection(
            encounter_id=thresholds.encounter_id,
            demands=tuple(demands),
            unresolved=tuple(unresolved),
        )
