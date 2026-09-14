from __future__ import annotations

"""Fill target-specific taunt-maintenance gaps using explicit refresh policy.

Canonical taunt duration and continuous-coverage truth belong to
RotationTankTauntMaintenanceService. This layer owns only candidate generation.
The caller must explicitly choose the initial application timestamp (when the
existing candidate does not already cover maintenance start) and a pre-expiry
refresh lead. No global taunt cadence or safety margin is invented here.

Existing target-correct casts are preserved. When a real uncovered boundary remains,
the service derives one exact application claim at ``gap_start - refresh_lead`` and
delegates skill/bar legality, target binding, and occupied-slot handling to the
existing RotationTankTauntCandidateService. The candidate is re-assessed after every
insertion, so already-useful casts can satisfy arbitrary portions of the window.
"""

from dataclasses import dataclass
import math
from pathlib import Path

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_plan import RotationActionKind
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_candidate_service import (
    RotationTankTauntActionClaim,
    RotationTankTauntCandidateProjection,
    RotationTankTauntCandidateService,
)
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
    RotationTankTauntMaintenanceService,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
)


@dataclass(frozen=True)
class RotationTankTauntMaintenanceRefreshPolicy:
    """Caller-owned refresh strategy for one maintenance requirement."""

    requirement_id: str
    refresh_lead_seconds: float
    initial_application_time_seconds: float | None = None
    action_sequence: int = 0
    action_kind: RotationActionKind = RotationActionKind.SKILL
    bar: str | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        requirement_id = str(self.requirement_id or "").strip()
        if not requirement_id:
            raise ValueError("tank taunt refresh policy requirement_id is required")
        object.__setattr__(self, "requirement_id", requirement_id)

        lead = float(self.refresh_lead_seconds)
        if not math.isfinite(lead) or lead < 0:
            raise ValueError("tank taunt refresh lead must be finite and non-negative")
        object.__setattr__(self, "refresh_lead_seconds", lead)

        if self.initial_application_time_seconds is not None:
            initial = float(self.initial_application_time_seconds)
            if not math.isfinite(initial) or initial < 0:
                raise ValueError(
                    "tank taunt initial application time must be finite and non-negative"
                )
            object.__setattr__(self, "initial_application_time_seconds", initial)

        sequence = int(self.action_sequence)
        if sequence < 0:
            raise ValueError("tank taunt refresh policy sequence cannot be negative")
        object.__setattr__(self, "action_sequence", sequence)

        kind = (
            self.action_kind
            if isinstance(self.action_kind, RotationActionKind)
            else RotationActionKind(str(self.action_kind))
        )
        if kind not in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
            raise ValueError("tank taunt refresh policy action must be skill or ultimate")
        object.__setattr__(self, "action_kind", kind)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("tank taunt refresh policy bar must be front or back")
            object.__setattr__(self, "bar", bar)

        object.__setattr__(
            self,
            "provenance",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.provenance
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class RotationTankTauntMaintenanceCandidateProjection:
    candidate: GeneratedRotationCandidate | None
    inserted_claims: tuple[RotationTankTauntActionClaim, ...] = ()
    preserved_requirement_ids: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.candidate is not None and not self.unresolved


class RotationTankTauntMaintenanceCandidateService:
    """Generate only the taunt applications needed to close maintenance gaps."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        maintenance_service: RotationTankTauntMaintenanceService | object | None = None,
        candidate_service: RotationTankTauntCandidateService | object | None = None,
    ) -> None:
        self.maintenance_service = maintenance_service or RotationTankTauntMaintenanceService(
            database_path
        )
        self.candidate_service = candidate_service or RotationTankTauntCandidateService(
            database_path
        )

    def project(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        requirements: tuple[RotationTankTauntMaintenanceRequirement, ...],
        policies: tuple[RotationTankTauntMaintenanceRefreshPolicy, ...],
        slot_requirements: tuple[RotationActionSlotRequirement, ...] = (),
    ) -> RotationTankTauntMaintenanceCandidateProjection:
        if not requirements:
            return RotationTankTauntMaintenanceCandidateProjection(
                candidate=None,
                unresolved=(
                    "tank taunt maintenance candidate generation unavailable: no maintenance requirement supplied",
                ),
            )

        requirement_by_id: dict[str, RotationTankTauntMaintenanceRequirement] = {}
        for requirement in requirements:
            if requirement.requirement_id in requirement_by_id:
                raise ValueError(
                    f"duplicate tank taunt maintenance requirement id: {requirement.requirement_id}"
                )
            requirement_by_id[requirement.requirement_id] = requirement

        policy_by_id: dict[str, RotationTankTauntMaintenanceRefreshPolicy] = {}
        for policy in policies:
            if policy.requirement_id in policy_by_id:
                raise ValueError(
                    f"duplicate tank taunt maintenance refresh policy id: {policy.requirement_id}"
                )
            if policy.requirement_id not in requirement_by_id:
                raise ValueError(
                    "tank taunt maintenance refresh policy references unknown requirement: "
                    f"{policy.requirement_id}"
                )
            policy_by_id[policy.requirement_id] = policy

        working = candidate
        inserted: list[RotationTankTauntActionClaim] = []
        preserved: list[str] = []
        unresolved: list[str] = []

        for requirement in requirements:
            assessment = self.maintenance_service.assess(
                plan=working.plan,
                requirement=requirement,
            )
            if not bool(getattr(assessment, "resolved", False)):
                messages = tuple(getattr(assessment, "unresolved", ())) or (
                    f"{requirement.requirement_id}: taunt maintenance evidence unresolved",
                )
                unresolved.extend(str(message) for message in messages)
                continue
            if bool(getattr(assessment, "satisfied", False)):
                preserved.append(requirement.requirement_id)
                continue

            policy = policy_by_id.get(requirement.requirement_id)
            if policy is None:
                unresolved.append(
                    f"{requirement.requirement_id}: explicit taunt maintenance refresh policy is required"
                )
                continue

            duration = float(getattr(assessment, "duration_seconds"))
            if policy.refresh_lead_seconds >= duration:
                unresolved.append(
                    f"{requirement.requirement_id}: refresh lead {policy.refresh_lead_seconds:g}s "
                    f"must be smaller than canonical taunt duration {duration:g}s"
                )
                continue
            if policy.bar is not None and requirement.bar is not None and policy.bar != requirement.bar:
                unresolved.append(
                    f"{requirement.requirement_id}: refresh policy bar {policy.bar} does not match "
                    f"maintenance requirement bar {requirement.bar}"
                )
                continue

            iteration = 0
            while not bool(getattr(assessment, "satisfied", False)):
                iteration += 1
                if iteration > 256:
                    unresolved.append(
                        f"{requirement.requirement_id}: taunt maintenance refresh generation exceeded deterministic safety bound"
                    )
                    break

                gaps = tuple(getattr(assessment, "uncovered_windows", ()))
                if not gaps:
                    unresolved.append(
                        f"{requirement.requirement_id}: taunt maintenance is unsatisfied but exposes no uncovered window"
                    )
                    break
                gap_start, _gap_end = gaps[0]

                at_maintenance_start = math.isclose(
                    float(gap_start),
                    requirement.active_start_seconds,
                    abs_tol=1e-9,
                )
                if at_maintenance_start:
                    if policy.initial_application_time_seconds is None:
                        unresolved.append(
                            f"{requirement.requirement_id}: maintenance starts uncovered and no exact initial taunt application time was supplied"
                        )
                        break
                    claim_time = float(policy.initial_application_time_seconds)
                    if claim_time > requirement.active_start_seconds + 1e-9:
                        unresolved.append(
                            f"{requirement.requirement_id}: initial taunt application at {claim_time:g}s occurs after "
                            f"maintenance start {requirement.active_start_seconds:g}s"
                        )
                        break
                    if claim_time + duration < requirement.active_start_seconds - 1e-9:
                        unresolved.append(
                            f"{requirement.requirement_id}: initial taunt application at {claim_time:g}s expires before "
                            f"maintenance start {requirement.active_start_seconds:g}s"
                        )
                        break
                else:
                    claim_time = float(gap_start) - policy.refresh_lead_seconds
                    if claim_time < 0:
                        unresolved.append(
                            f"{requirement.requirement_id}: refresh policy places taunt before plan start"
                        )
                        break

                if claim_time > working.plan.duration_seconds + 1e-9:
                    unresolved.append(
                        f"{requirement.requirement_id}: refresh claim at {claim_time:g}s occurs after rotation plan duration"
                    )
                    break

                application_id = (
                    f"{requirement.requirement_id}:maintenance_refresh:{iteration:03d}"
                )
                application_requirement = RotationTankTauntApplicationRequirement(
                    requirement_id=application_id,
                    source_skill_name=requirement.source_skill_name,
                    window_start_seconds=claim_time,
                    window_end_seconds=claim_time,
                    minimum_applications=1,
                    bar=policy.bar if policy.bar is not None else requirement.bar,
                    target_key=requirement.target_key,
                    provenance=tuple(requirement.provenance)
                    + tuple(policy.provenance)
                    + ("derived from explicit target-specific taunt maintenance gap",),
                )
                claim = RotationTankTauntActionClaim(
                    requirement_id=application_id,
                    action_time_seconds=claim_time,
                    action_sequence=policy.action_sequence,
                    action_kind=policy.action_kind,
                    bar=policy.bar if policy.bar is not None else requirement.bar,
                    target_key=requirement.target_key,
                    provenance=tuple(policy.provenance),
                )

                projection: RotationTankTauntCandidateProjection = self.candidate_service.project(
                    candidate=working,
                    requirements=(application_requirement,),
                    claims=(claim,),
                    slot_requirements=slot_requirements,
                )
                if projection.candidate is None:
                    unresolved.extend(
                        projection.unresolved
                        or (
                            f"{requirement.requirement_id}: taunt maintenance refresh claim could not be projected",
                        )
                    )
                    break

                working = projection.candidate
                inserted.extend(projection.inserted_claims)
                next_assessment = self.maintenance_service.assess(
                    plan=working.plan,
                    requirement=requirement,
                )
                if not bool(getattr(next_assessment, "resolved", False)):
                    unresolved.extend(
                        tuple(getattr(next_assessment, "unresolved", ()))
                        or (
                            f"{requirement.requirement_id}: taunt maintenance became unresolved after refresh projection",
                        )
                    )
                    break
                if tuple(getattr(next_assessment, "uncovered_windows", ())) == gaps:
                    unresolved.append(
                        f"{requirement.requirement_id}: refresh claim made no progress toward continuous taunt maintenance"
                    )
                    break
                assessment = next_assessment

            if unresolved:
                break

        if unresolved:
            return RotationTankTauntMaintenanceCandidateProjection(
                candidate=None,
                inserted_claims=tuple(inserted),
                preserved_requirement_ids=tuple(preserved),
                unresolved=tuple(dict.fromkeys(str(item) for item in unresolved if str(item))),
            )

        final_evidence = self.maintenance_service.evaluate_candidate(
            candidate=working,
            requirements=requirements,
        )
        if final_evidence.satisfied is not True:
            return RotationTankTauntMaintenanceCandidateProjection(
                candidate=None,
                inserted_claims=tuple(inserted),
                preserved_requirement_ids=tuple(preserved),
                unresolved=tuple(final_evidence.reasons),
            )

        return RotationTankTauntMaintenanceCandidateProjection(
            candidate=working,
            inserted_claims=tuple(inserted),
            preserved_requirement_ids=tuple(preserved),
        )


__all__ = [
    "RotationTankTauntMaintenanceCandidateProjection",
    "RotationTankTauntMaintenanceCandidateService",
    "RotationTankTauntMaintenanceRefreshPolicy",
]
