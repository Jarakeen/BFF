from __future__ import annotations

"""Read-only advisory review for one explicit RaidPlan.

The Adviser consumes the same exact saved-build scope and canonical capability evidence
used by Coverage. It never mutates RaidPlan, saved builds, assignments, or Optimization
state. Findings distinguish real plan gaps from conditional execution and Foundry evidence
debt so incomplete canonical data is never presented as a player/build recommendation.
"""

from dataclasses import dataclass
from typing import Iterable

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService
from services.raid_unique_support_set_capability_service import (
    RaidUniqueSupportSetCapabilityService,
)
from services.saved_build_capability_service import summarize_raid_coverage


_VALID_CATEGORIES = frozenset(
    {"blocker", "coverage_gap", "conditional", "redundancy", "data_gap"}
)
_VALID_PRIORITIES = frozenset({"high", "medium", "low"})


@dataclass(frozen=True)
class RaidPlanAdviserFinding:
    category: str
    priority: str
    subject: str
    recommendation: str
    evidence: str

    def __post_init__(self) -> None:
        if self.category not in _VALID_CATEGORIES:
            raise ValueError(f"unsupported adviser category: {self.category}")
        if self.priority not in _VALID_PRIORITIES:
            raise ValueError(f"unsupported adviser priority: {self.priority}")
        if not self.subject.strip() or not self.recommendation.strip() or not self.evidence.strip():
            raise ValueError("adviser findings require subject, recommendation, and evidence")


@dataclass(frozen=True)
class RaidPlanAdviserReview:
    plan_id: str
    plan_name: str
    trial_id: str
    resolved_build_count: int
    named_member_count: int
    total_chairs: int
    findings: tuple[RaidPlanAdviserFinding, ...]

    @property
    def blocker_count(self) -> int:
        return sum(item.category == "blocker" for item in self.findings)

    @property
    def actionable_count(self) -> int:
        return sum(item.category in {"blocker", "coverage_gap", "conditional", "redundancy"} for item in self.findings)


class RaidPlanOptimizerAdviserService:
    """Explain plan weaknesses/opportunities without rewriting the plan."""

    def __init__(
        self,
        capability_service,
        *,
        scope_service: RaidPlanCoverageScopeService | None = None,
        unique_set_service: RaidUniqueSupportSetCapabilityService | None = None,
    ) -> None:
        self.capability_service = capability_service
        self.scope_service = scope_service or RaidPlanCoverageScopeService()
        self.unique_set_service = unique_set_service or RaidUniqueSupportSetCapabilityService()

    def review(
        self,
        *,
        raid_plan: RaidPlan,
        saved_builds: Iterable[PlayerBuild],
        total_chairs: int = 12,
    ) -> RaidPlanAdviserReview:
        if not isinstance(raid_plan, RaidPlan):
            raise TypeError("optimizer adviser requires RaidPlan")

        saved = tuple(saved_builds)
        required_names = tuple(
            row.display_name
            for row in DEFAULT_RAID_COVERAGE_PROFILE.requirements
            if row.required
        )
        scope = self.scope_service.compose(
            raid_plan=raid_plan,
            saved_builds=saved,
            coverage_effect_names=required_names,
            total_chairs=total_chairs,
        )
        findings: list[RaidPlanAdviserFinding] = []

        open_chairs = max(0, int(total_chairs) - scope.named_members)
        if open_chairs:
            findings.append(
                RaidPlanAdviserFinding(
                    category="blocker",
                    priority="high",
                    subject=f"{open_chairs} open chair(s)",
                    recommendation="Name players for the remaining chairs before treating this plan as raid-ready.",
                    evidence=f"Raid Plan has {scope.named_members}/{int(total_chairs)} named chairs.",
                )
            )

        for unresolved in scope.unresolved:
            findings.append(
                RaidPlanAdviserFinding(
                    category="blocker",
                    priority="high",
                    subject="Unresolved selected build",
                    recommendation="Resolve the chair to one exact saved build before optimizing around it.",
                    evidence=str(unresolved),
                )
            )

        audits: list[tuple[PlayerBuild, object]] = []
        for build in scope.resolved_builds:
            audit = self.capability_service.audit_build(build)
            audits.append((build, audit))
            gaps = tuple(getattr(audit, "capability_resolution_gaps", ()) or ())
            if gaps:
                label = str(build.Name or build.Gamertag or build.BuildName or "Unnamed build")
                findings.append(
                    RaidPlanAdviserFinding(
                        category="data_gap",
                        priority="low",
                        subject=f"{label}: canonical evidence incomplete",
                        recommendation="Review Foundry's unresolved capability evidence before changing the player's build solely to clear this warning.",
                        evidence=f"{len(gaps)} capability-resolution gap(s); first: {gaps[0]}",
                    )
                )

        snapshot = summarize_raid_coverage(DEFAULT_RAID_COVERAGE_PROFILE, audits)
        snapshot = self.unique_set_service.overlay(snapshot, scope.resolved_builds)

        for requirement in DEFAULT_RAID_COVERAGE_PROFILE.requirements:
            if not requirement.required:
                continue
            effect = requirement.display_name
            state = snapshot.status.get(effect, "unverified")
            providers = tuple(snapshot.providers.get(effect, ()))
            conditional = tuple(snapshot.conditional_providers.get(effect, ()))
            if state == "not_found":
                findings.append(
                    RaidPlanAdviserFinding(
                        category="coverage_gap",
                        priority="medium",
                        subject=effect,
                        recommendation=f"Review whether this plan needs a provider for {effect} and, if so, which chair should own it.",
                        evidence="Canonical static capability audit found no provider on the resolved selected builds.",
                    )
                )
            elif state == "conditional":
                findings.append(
                    RaidPlanAdviserFinding(
                        category="conditional",
                        priority="medium",
                        subject=effect,
                        recommendation=f"Verify the trigger/rotation responsibility that makes {effect} reliable in this plan.",
                        evidence="Static capability is conditional via: " + ", ".join(conditional),
                    )
                )
            elif state == "unverified":
                findings.append(
                    RaidPlanAdviserFinding(
                        category="data_gap",
                        priority="low",
                        subject=effect,
                        recommendation="Do not change the team from this row alone; Foundry lacks enough reviewed static evidence to judge it.",
                        evidence="Coverage state is Unverified, not Missing.",
                    )
                )
            if len(providers) > 1:
                findings.append(
                    RaidPlanAdviserFinding(
                        category="redundancy",
                        priority="low",
                        subject=effect,
                        recommendation=f"Confirm whether overlapping {effect} providers are intentional before freeing either build slot.",
                        evidence="Multiple static providers: " + ", ".join(providers),
                    )
                )

        for item in self.unique_set_service.evaluate(scope.resolved_builds):
            if item.state != "conditional":
                continue
            findings.append(
                RaidPlanAdviserFinding(
                    category="conditional",
                    priority="medium",
                    subject=item.effect_name,
                    recommendation=f"Confirm {item.provider}'s trigger and execution responsibility for {item.effect_name}; equipment proves capability, not uptime.",
                    evidence=(
                        f"Reviewed support set is active on {', '.join(item.qualifying_bars)} bar(s) "
                        f"({item.front_pieces} front / {item.back_pieces} back pieces)."
                    ),
                )
            )

        priority_rank = {"high": 0, "medium": 1, "low": 2}
        category_rank = {
            "blocker": 0,
            "coverage_gap": 1,
            "conditional": 2,
            "redundancy": 3,
            "data_gap": 4,
        }
        ordered = tuple(
            sorted(
                findings,
                key=lambda item: (
                    priority_rank[item.priority],
                    category_rank[item.category],
                    item.subject.casefold(),
                    item.evidence.casefold(),
                ),
            )
        )
        return RaidPlanAdviserReview(
            plan_id=raid_plan.plan_id,
            plan_name=raid_plan.name,
            trial_id=raid_plan.trial_id,
            resolved_build_count=len(scope.resolved_builds),
            named_member_count=scope.named_members,
            total_chairs=int(total_chairs),
            findings=ordered,
        )


__all__ = [
    "RaidPlanAdviserFinding",
    "RaidPlanAdviserReview",
    "RaidPlanOptimizerAdviserService",
]
