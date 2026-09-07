from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.encounter_boss_guide import BossGuideTimelineFact, EncounterBossGuide


@dataclass(frozen=True)
class EncounterRotationDemandPolicy:
    """Explicit role interpretation for one reviewed canonical encounter fact.

    Encounter evidence owns *when* the event occurs. This policy owns what the
    rotation should prepare for. Neither side is inferred from prose or fact names.
    """

    fact_key: str
    kind: RotationDemandKind
    pattern: RotationDemandPattern
    lead_seconds: float = 0.0
    point_window_seconds: float | None = None
    target_count: int = 1

    def __post_init__(self) -> None:
        key = str(self.fact_key or "").strip()
        if not key:
            raise ValueError("encounter rotation demand policy requires a fact_key")
        object.__setattr__(self, "fact_key", key)

        if not isinstance(self.kind, RotationDemandKind):
            object.__setattr__(self, "kind", RotationDemandKind(str(self.kind)))
        if not isinstance(self.pattern, RotationDemandPattern):
            object.__setattr__(self, "pattern", RotationDemandPattern(str(self.pattern)))

        lead = float(self.lead_seconds)
        if not math.isfinite(lead) or lead < 0:
            raise ValueError("encounter rotation demand lead_seconds must be finite and non-negative")
        object.__setattr__(self, "lead_seconds", lead)

        if self.point_window_seconds is not None:
            width = float(self.point_window_seconds)
            if not math.isfinite(width) or width <= 0:
                raise ValueError(
                    "encounter rotation demand point_window_seconds must be finite and positive"
                )
            object.__setattr__(self, "point_window_seconds", width)

        count = int(self.target_count)
        if count <= 0:
            raise ValueError("encounter rotation demand target_count must be positive")
        object.__setattr__(self, "target_count", count)


@dataclass(frozen=True)
class EncounterRotationDemandProjection:
    encounter_id: str
    demands: tuple[RotationDemandWindow, ...]
    unresolved: tuple[str, ...]


def _number(payload: dict, key: str) -> float | None:
    if key not in payload:
        return None
    raw = payload.get(key)
    if isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _label(fact: BossGuideTimelineFact) -> str:
    payload = fact.payload
    return str(
        payload.get("label")
        or payload.get("name")
        or fact.fact_key.replace("_", " ").strip().title()
        or "Encounter Demand"
    ).strip()


def _clock_window(
    fact: BossGuideTimelineFact,
    policy: EncounterRotationDemandPolicy,
) -> tuple[float, float] | None:
    payload = fact.payload
    start = _number(payload, "start_seconds")
    end = _number(payload, "end_seconds")

    if start is not None or end is not None:
        if start is None or end is None or end <= start:
            return None
        return max(0.0, start - policy.lead_seconds), end

    point = _number(payload, "time_seconds")
    if point is None:
        point = _number(payload, "at_seconds")
    if point is None:
        return None
    if policy.point_window_seconds is None:
        return None

    return (
        max(0.0, point - policy.lead_seconds),
        point + policy.point_window_seconds,
    )


class EncounterRotationDemandService:
    """Bridge reviewed, clock-timed encounter facts into rotation demand windows.

    Health thresholds, phase percentages, prose descriptions, and ambiguous timing
    remain unresolved. Converting a boss-health threshold to wall-clock time would
    require a fight-duration/DPS projection and belongs to a later layer.
    """

    def project(
        self,
        *,
        guide: EncounterBossGuide,
        policies: tuple[EncounterRotationDemandPolicy, ...],
    ) -> EncounterRotationDemandProjection:
        policy_by_key: dict[str, EncounterRotationDemandPolicy] = {}
        for policy in policies:
            if policy.fact_key in policy_by_key:
                raise ValueError(
                    f"duplicate encounter rotation demand policy for {policy.fact_key}"
                )
            policy_by_key[policy.fact_key] = policy

        facts_by_key: dict[str, BossGuideTimelineFact] = {}
        for fact in guide.timeline_facts:
            if fact.fact_key in facts_by_key:
                raise ValueError(
                    f"multiple canonical timeline facts share fact_key {fact.fact_key!r}"
                )
            facts_by_key[fact.fact_key] = fact

        demands: list[RotationDemandWindow] = []
        unresolved: list[str] = []

        for key, policy in policy_by_key.items():
            fact = facts_by_key.get(key)
            if fact is None:
                unresolved.append(
                    f"{key}: no canonical encounter timeline fact is available"
                )
                continue
            if not str(fact.review_status or "").casefold().startswith("reviewed"):
                unresolved.append(
                    f"{key}: canonical timeline fact is not reviewed ({fact.review_status or 'unknown'})"
                )
                continue
            if fact.evidence_count <= 0:
                unresolved.append(
                    f"{key}: reviewed canonical timeline fact has no persisted evidence rows"
                )
                continue

            window = _clock_window(fact, policy)
            if window is None:
                unresolved.append(
                    f"{key}: canonical encounter fact has no complete explicit clock window; "
                    "health/phase thresholds are not converted to seconds"
                )
                continue

            start, end = window
            demands.append(
                RotationDemandWindow(
                    name=_label(fact),
                    start_seconds=start,
                    end_seconds=end,
                    kind=policy.kind,
                    pattern=policy.pattern,
                    target_count=policy.target_count,
                )
            )

        demands.sort(key=lambda item: (item.start_seconds, item.end_seconds, item.name))
        return EncounterRotationDemandProjection(
            encounter_id=guide.encounter_id,
            demands=tuple(demands),
            unresolved=tuple(unresolved),
        )
