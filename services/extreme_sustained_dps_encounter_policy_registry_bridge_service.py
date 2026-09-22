from __future__ import annotations

"""Bridge reviewed Rotation encounter-demand policy into Extreme sustained-DPS search."""

from dataclasses import dataclass

from minmax.rotation_demand_window import RotationDemandWindow
from services.extreme_sustained_dps_encounter_policy_frontier_service import (
    ExtremeSustainedDPSEncounterPolicyChoice,
    ExtremeSustainedDPSEncounterPolicyFrontier,
    ExtremeSustainedDPSEncounterPolicyFrontierService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSEncounterThresholdDemandProjection:
    demands: tuple[RotationDemandWindow, ...]
    denominator_proven: bool
    source: str
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        source = str(self.source or "").strip()
        if not source:
            raise ValueError(
                "sustained-DPS threshold encounter-demand projection requires source"
            )
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "demands", tuple(self.demands))
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )


class ExtremeSustainedDPSEncounterPolicyRegistryBridgeService:
    """Reuse reviewed Rotation policy rather than inventing Extreme encounter timing."""

    def __init__(
        self,
        *,
        registry: object,
        guide_service: object,
        demand_service: object,
    ) -> None:
        self.registry = registry
        self.guide_service = guide_service
        self.demand_service = demand_service

    def build(
        self,
        encounter_id: str,
        *,
        threshold_projection: (
            ExtremeSustainedDPSEncounterThresholdDemandProjection | None
        ) = None,
    ) -> ExtremeSustainedDPSEncounterPolicyFrontier:
        encounter = str(encounter_id or "").strip()
        if not encounter:
            raise ValueError(
                "sustained-DPS encounter-policy bridge requires encounter_id"
            )

        entry = self.registry.entry_for(encounter)
        unresolved: list[str] = []
        evidence: list[str] = [
            f"Selected canonical encounter: {encounter}",
        ]

        if entry is None:
            unresolved.append(
                "No reviewed Rotation encounter-demand policy registry entry is available"
            )
            return ExtremeSustainedDPSEncounterPolicyFrontierService.build(
                (
                    ExtremeSustainedDPSEncounterPolicyChoice(
                        policy_id=f"encounter:{encounter}",
                        demands=(),
                        unresolved=tuple(unresolved),
                    ),
                ),
                denominator_proven=False,
                source="reviewed Rotation encounter-demand policy registry",
            )

        blockers = tuple(getattr(entry, "review_blockers", ()) or ())
        for blocker in blockers:
            key = str(getattr(blocker, "key", "") or "").strip()
            needed = str(
                getattr(blocker, "needed_evidence", "") or ""
            ).strip()
            unresolved.append(
                "Encounter policy review blocker"
                + (f" {key}" if key else "")
                + (f": {needed}" if needed else "")
            )

        clock_policies = tuple(getattr(entry, "clock_policies", ()) or ())
        threshold_policies = tuple(
            getattr(entry, "threshold_policies", ()) or ()
        )
        evidence.extend(
            (
                f"Reviewed clock policies: {len(clock_policies)}",
                f"Reviewed threshold policies: {len(threshold_policies)}",
                f"Review blockers: {len(blockers)}",
            )
        )

        demands: list[RotationDemandWindow] = []

        if clock_policies:
            guide = self.guide_service.get(encounter)
            projection = self.demand_service.project(
                guide=guide,
                policies=clock_policies,
            )
            projection_unresolved = tuple(
                getattr(projection, "unresolved", ()) or ()
            )
            unresolved.extend(
                f"Clock policy: {item}"
                for item in projection_unresolved
            )
            demands.extend(tuple(getattr(projection, "demands", ()) or ()))
            evidence.append(
                f"Resolved clock demand windows: {len(tuple(getattr(projection, 'demands', ()) or ()))}"
            )

        if threshold_policies:
            if threshold_projection is None:
                unresolved.append(
                    "Reviewed threshold encounter policy requires an explicit proven threshold-to-clock demand projection"
                )
            else:
                unresolved.extend(
                    f"Threshold policy: {item}"
                    for item in threshold_projection.unresolved
                )
                if not threshold_projection.denominator_proven:
                    unresolved.append(
                        "Threshold-to-clock encounter demand denominator is not proven complete"
                    )
                demands.extend(threshold_projection.demands)
                evidence.extend(
                    (
                        f"Resolved threshold demand windows: {len(threshold_projection.demands)}",
                        f"Threshold projection source: {threshold_projection.source}",
                    )
                )

        deduped = tuple(dict.fromkeys(unresolved))
        complete = not deduped

        if not clock_policies and not threshold_policies and not blockers:
            evidence.append(
                "Reviewed encounter policy explicitly contains no rotation demands"
            )

        choice = ExtremeSustainedDPSEncounterPolicyChoice(
            policy_id=f"encounter:{encounter}",
            demands=tuple(demands),
            evidence=tuple(evidence),
            unresolved=deduped,
        )
        return ExtremeSustainedDPSEncounterPolicyFrontierService.build(
            (choice,),
            denominator_proven=complete,
            source="reviewed Rotation encounter-demand policy registry",
        )


__all__ = [
    "ExtremeSustainedDPSEncounterPolicyRegistryBridgeService",
    "ExtremeSustainedDPSEncounterThresholdDemandProjection",
]
