from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandWindow
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerDemandEvidenceProvider,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)
from services.rotation_plan_runtime_build_context_service import (
    RotationRuntimeBuildContextResolver,
)


@dataclass(frozen=True)
class RotationCandidateHealerDemandWindowOutput:
    """Modeled healer output retained for one explicit encounter demand window."""

    evidence: RotationHealerDemandHealingEvidence
    modeled_healing_per_demand_second: float | None

    def __post_init__(self) -> None:
        value = self.modeled_healing_per_demand_second
        if value is None:
            return
        value = float(value)
        if not isfinite(value) or value < 0.0:
            raise ValueError(
                "healer demand-window modeled output must be finite and non-negative"
            )
        object.__setattr__(self, "modeled_healing_per_demand_second", value)

    @property
    def demand(self) -> RotationDemandWindow:
        return self.evidence.demand

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(self.evidence.unresolved)


@dataclass(frozen=True)
class RotationCandidateHealerMultiDemandOutput:
    """Per-window healer evidence plus a conservative weakest-window floor.

    Every healing demand remains inspectable independently. The scalar role-output
    value is the lowest resolved modeled-healing-per-demand-second value across the
    required windows. This deliberately avoids averaging unlike encounter moments,
    which could allow excess modeled healing in one window to hide weak output in
    another. It is a comparison floor, not a claim about required HPS or survival.
    """

    candidate_id: str
    windows: tuple[RotationCandidateHealerDemandWindowOutput, ...]
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("multi-demand healer output candidate_id is required")
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "windows", tuple(self.windows))
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip() for item in self.unresolved if str(item).strip()
                )
            ),
        )

    @property
    def weakest_window_value(self) -> float | None:
        if self.unresolved or not self.windows:
            return None
        values = tuple(
            item.modeled_healing_per_demand_second for item in self.windows
        )
        if any(value is None for value in values):
            return None
        return min(float(value) for value in values if value is not None)


class RotationCandidateHealerMultiDemandRoleOutputService:
    """Evaluate healer candidates across every supplied encounter healing window.

    The supplying demand-evidence provider remains authoritative for direct,
    periodic, delayed, build, runtime, and special-activation consequences. This
    service only evaluates each explicit healing obligation and exposes a
    conservative weakest-window comparison value to the existing role-aware ranker.

    Exact-time runtime build context remains caller-owned. When supplied after final
    recovery stabilization, the same resolver is forwarded unchanged to every demand
    evidence evaluation so direct, periodic, delayed, and channel magnitude all bind
    to the final schedule rather than a seed-plan snapshot.

    No demand weighting, target-count multiplication, required-HPS threshold, or
    survival claim is invented here. Unknown evidence in any required window keeps
    the candidate's aggregate healer role output unknown.
    """

    def __init__(
        self,
        *,
        demands: tuple[RotationDemandWindow, ...],
        demand_evidence_provider: RotationCandidateHealerDemandEvidenceProvider,
    ) -> None:
        demands = tuple(demands)
        if not demands:
            raise ValueError("multi-demand healer role output requires at least one demand")
        if any(demand.kind is not RotationDemandKind.HEALING for demand in demands):
            raise ValueError("multi-demand healer role output accepts only healing demands")

        seen: set[str] = set()
        for demand in demands:
            key = demand.name.casefold()
            if key in seen:
                raise ValueError(f"duplicate healer demand name: {demand.name!r}")
            seen.add(key)

        self.demands = demands
        self.demand_evidence_provider = demand_evidence_provider

    def evaluate_windows(
        self,
        candidate: GeneratedRotationCandidate,
        *,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
    ) -> RotationCandidateHealerMultiDemandOutput:
        windows: list[RotationCandidateHealerDemandWindowOutput] = []
        unresolved: list[str] = []

        for demand in self.demands:
            demand_kwargs = {
                "candidate": candidate,
                "demand": demand,
            }
            if runtime_build_context_resolver is not None:
                demand_kwargs["runtime_build_context_resolver"] = (
                    runtime_build_context_resolver
                )
            evidence = self.demand_evidence_provider.evaluate_demand(**demand_kwargs)
            if evidence.demand != demand:
                raise ValueError(
                    "rotation healer demand evidence mismatch: provider returned a "
                    f"different demand window for {demand.name!r}"
                )

            demand_unresolved = tuple(evidence.unresolved)
            unresolved.extend(
                f"{demand.name}: {message}" for message in demand_unresolved
            )
            value = None
            if not demand_unresolved:
                value = (
                    float(evidence.modeled_total_healing) / demand.duration_seconds
                )
            windows.append(
                RotationCandidateHealerDemandWindowOutput(
                    evidence=evidence,
                    modeled_healing_per_demand_second=value,
                )
            )

        return RotationCandidateHealerMultiDemandOutput(
            candidate_id=candidate.candidate_id,
            windows=tuple(windows),
            unresolved=tuple(unresolved),
        )

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
        *,
        runtime_build_context_resolver: RotationRuntimeBuildContextResolver | None = None,
    ) -> RotationCandidateRoleOutputEvidence:
        result = self.evaluate_windows(
            candidate,
            runtime_build_context_resolver=runtime_build_context_resolver,
        )
        return RotationCandidateRoleOutputEvidence(
            candidate_id=candidate.candidate_id,
            value=result.weakest_window_value,
            unresolved=result.unresolved,
        )


__all__ = [
    "RotationCandidateHealerDemandWindowOutput",
    "RotationCandidateHealerMultiDemandOutput",
    "RotationCandidateHealerMultiDemandRoleOutputService",
]
