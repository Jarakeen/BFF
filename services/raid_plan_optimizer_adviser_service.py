from __future__ import annotations

"""Read-only advisory review for one explicit RaidPlan.

The Adviser consumes the same exact saved-build scope and canonical capability evidence
used by Coverage. It never mutates RaidPlan, saved builds, assignments, or Optimization
state. Findings distinguish real plan gaps from conditional execution and Foundry evidence
debt so incomplete canonical data is never presented as a player/build recommendation.
"""

from dataclasses import dataclass
from typing import Iterable

from engine.config import DEFAULT_DATABASE
from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from services.raid_plan_coverage_assignment_service import (
    RaidPlanCoverageAssignmentService,
)
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService
from services.raid_planned_gear_coverage_service import (
    PlannedGearCoverageProvider,
    RaidPlannedGearCoverageService,
)
from services.raid_planned_skill_coverage_service import (
    PlannedSkillCoverageProvider,
    RaidPlannedSkillCoverageService,
)
from services.raid_unique_support_set_capability_service import (
    RaidUniqueSupportSetCapabilityService,
)
from services.raid_unique_support_set_catalog import UNIQUE_SUPPORT_SET_NAMES
from services.saved_build_capability_service import summarize_raid_coverage


_VALID_CATEGORIES = frozenset(
    {"blocker", "coverage_gap", "conditional", "redundancy", "data_gap"}
)
_VALID_PRIORITIES = frozenset({"high", "medium", "low"})
_VALID_CONFIDENCE = frozenset({"high", "medium", "low", "unknown"})


@dataclass(frozen=True)
class RaidPlanAdviserFinding:
    category: str
    priority: str
    subject: str
    recommendation: str
    evidence: str
    current_state: str = "Review required"
    proposed_state: str = "No automatic change"
    confidence: str = "unknown"
    affected_seats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.category not in _VALID_CATEGORIES:
            raise ValueError(f"unsupported adviser category: {self.category}")
        if self.priority not in _VALID_PRIORITIES:
            raise ValueError(f"unsupported adviser priority: {self.priority}")
        if self.confidence not in _VALID_CONFIDENCE:
            raise ValueError(f"unsupported adviser confidence: {self.confidence}")
        if not self.subject.strip() or not self.recommendation.strip() or not self.evidence.strip():
            raise ValueError("adviser findings require subject, recommendation, and evidence")
        object.__setattr__(
            self,
            "affected_seats",
            tuple(
                dict.fromkeys(
                    str(value or "").strip()
                    for value in self.affected_seats
                    if str(value or "").strip()
                )
            ),
        )


@dataclass(frozen=True)
class RaidPlanAdviserReview:
    plan_id: str
    plan_name: str
    trial_id: str
    resolved_build_count: int
    named_member_count: int
    total_chairs: int
    required_effect_count: int
    covered_effect_count: int
    conditional_effect_count: int
    planned_unproven_effect_count: int
    ownership_attention_effect_count: int
    missing_effect_count: int
    unverified_effect_count: int
    findings: tuple[RaidPlanAdviserFinding, ...]

    @property
    def blocker_count(self) -> int:
        return sum(item.category == "blocker" for item in self.findings)

    @property
    def actionable_count(self) -> int:
        return sum(item.category in {"blocker", "coverage_gap", "conditional", "redundancy"} for item in self.findings)

    @property
    def coverage_summary(self) -> str:
        return (
            f"{self.covered_effect_count}/{self.required_effect_count} verified • "
            f"{self.conditional_effect_count} conditional • "
            f"{self.planned_unproven_effect_count} planned/unproven • "
            f"{self.ownership_attention_effect_count} needs owner • "
            f"{self.missing_effect_count} missing • "
            f"{self.unverified_effect_count} unverified"
        )


class RaidPlanOptimizerAdviserService:
    """Explain plan weaknesses/opportunities without rewriting the plan."""

    def __init__(
        self,
        capability_service,
        *,
        scope_service: RaidPlanCoverageScopeService | None = None,
        unique_set_service: RaidUniqueSupportSetCapabilityService | None = None,
        assignment_service: RaidPlanCoverageAssignmentService | None = None,
        planned_gear_service: RaidPlannedGearCoverageService | None = None,
        planned_skill_service: RaidPlannedSkillCoverageService | None = None,
    ) -> None:
        self.capability_service = capability_service
        self.scope_service = scope_service or RaidPlanCoverageScopeService()
        self.unique_set_service = unique_set_service or RaidUniqueSupportSetCapabilityService()
        self.assignment_service = assignment_service or RaidPlanCoverageAssignmentService()
        self.planned_gear_service = planned_gear_service or RaidPlannedGearCoverageService(
            DEFAULT_DATABASE
        )
        self.planned_skill_service = planned_skill_service or RaidPlannedSkillCoverageService(
            DEFAULT_DATABASE
        )

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
        coverage_names = tuple(dict.fromkeys((*required_names, *UNIQUE_SUPPORT_SET_NAMES)))
        scope = self.scope_service.compose(
            raid_plan=raid_plan,
            saved_builds=saved,
            coverage_effect_names=coverage_names,
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
                    current_state=f"{scope.named_members}/{int(total_chairs)} chairs named",
                    proposed_state="Name every required raid chair",
                    confidence="high",
                    affected_seats=("Open chairs",),
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
                    current_state="Selected build does not resolve",
                    proposed_state="Bind one exact saved build",
                    confidence="high",
                    affected_seats=("Unresolved chair",),
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
                        current_state=f"{len(gaps)} unresolved evidence row(s)",
                        proposed_state="Resolve canonical evidence; do not alter the build by inference",
                        confidence="high",
                        affected_seats=(label,),
                    )
                )

        snapshot = summarize_raid_coverage(DEFAULT_RAID_COVERAGE_PROFILE, audits)
        snapshot = self.unique_set_service.overlay(snapshot, scope.resolved_builds)
        snapshot = self.planned_gear_service.overlay(
            snapshot,
            tuple(
                PlannedGearCoverageProvider(
                    seat_id=row.seat_id,
                    provider_label=row.player_label,
                    gear_sets=row.gear_sets,
                )
                for row in scope.planned_gear
            ),
            effect_names=coverage_names,
        )
        snapshot = self.planned_skill_service.overlay(
            snapshot,
            tuple(
                PlannedSkillCoverageProvider(
                    seat_id=row.seat_id,
                    provider_label=row.player_label,
                    eso_class=row.eso_class,
                    skills=row.skills,
                )
                for row in scope.planned_skills
            ),
            effect_names=coverage_names,
        )

        assignment_reviews = {
            effect_name: self.assignment_service.review(
                effect_name=effect_name,
                scope=scope,
                snapshot=snapshot,
            )
            for effect_name in coverage_names
        }

        for effect in coverage_names:
            state = snapshot.status.get(effect, "unverified")
            providers = tuple(snapshot.providers.get(effect, ()))
            conditional = tuple(snapshot.conditional_providers.get(effect, ()))
            ownership = assignment_reviews[effect]
            if (
                effect not in required_names
                and ownership.state == "gap"
                and not providers
                and not conditional
            ):
                continue
            if ownership.state == "gap":
                findings.append(
                    RaidPlanAdviserFinding(
                        category="coverage_gap",
                        priority="medium",
                        subject=effect,
                        recommendation=f"Review whether this plan needs a provider for {effect} and, if so, which chair should own it.",
                        evidence="Canonical saved-build, planned-gear, and planned-skill evidence found no provider.",
                        current_state="No canonical provider found",
                        proposed_state="Assign and verify one exact provider",
                        confidence="high",
                        affected_seats=("Unassigned",),
                    )
                )
            elif ownership.state == "assigned_unproven":
                findings.append(
                    RaidPlanAdviserFinding(
                        category="conditional",
                        priority="medium",
                        subject=effect,
                        recommendation=(
                            f"Keep {effect} assigned to {', '.join(ownership.primary)}, but complete or verify the exact gear/skill/build source before optimizing around it."
                        ),
                        evidence=(
                            "Raid Plan assignment intent exists, but canonical saved-build, planned-gear, and planned-skill evidence does not prove the assigned provider source."
                        ),
                        current_state="Assigned provider; source unproven",
                        proposed_state="Verify one exact compatible provider source",
                        confidence="high",
                        affected_seats=ownership.primary,
                    )
                )
            elif ownership.state == "backup_only":
                findings.append(
                    RaidPlanAdviserFinding(
                        category="conditional",
                        priority="medium",
                        subject=effect,
                        recommendation=f"Promote or assign a primary owner for {effect}; current evidence resolves only through a backup provider.",
                        evidence="Coverage assignment review found supported or conditional backup evidence without a primary owner.",
                        current_state="Backup provider only",
                        proposed_state="Assign and verify a primary provider",
                        confidence="high",
                        affected_seats=ownership.backup,
                    )
                )
            elif ownership.state == "unassigned_available":
                available = tuple(dict.fromkeys((*providers, *conditional)))
                findings.append(
                    RaidPlanAdviserFinding(
                        category="conditional",
                        priority="medium",
                        subject=effect,
                        recommendation=f"Assign explicit ownership for {effect} to one proven or conditional provider, then verify any trigger/uptime requirement before relying on it.",
                        evidence="Provider evidence exists, but the Raid Plan does not name a primary owner.",
                        current_state="Provider exists; ownership unassigned",
                        proposed_state="Assign one explicit primary owner",
                        confidence="high",
                        affected_seats=available,
                    )
                )
            elif ownership.state == "assigned_conditional" or state == "conditional":
                findings.append(
                    RaidPlanAdviserFinding(
                        category="conditional",
                        priority="medium",
                        subject=effect,
                        recommendation=f"Verify the trigger/rotation responsibility that makes {effect} reliable in this plan.",
                        evidence="Static capability is conditional via: " + ", ".join(conditional),
                        current_state="Provider exists; execution is conditional",
                        proposed_state="Verify trigger and rotation responsibility",
                        confidence="medium",
                        affected_seats=ownership.primary or conditional,
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
                        current_state="Coverage unverified",
                        proposed_state="Resolve evidence before proposing a team change",
                        confidence="unknown",
                        affected_seats=("Evidence review",),
                    )
                )
            if ownership.duplicate_primary or len(providers) > 1:
                duplicate_providers = ownership.primary if ownership.duplicate_primary else providers
                findings.append(
                    RaidPlanAdviserFinding(
                        category="redundancy",
                        priority="low",
                        subject=effect,
                        recommendation=f"Confirm whether overlapping {effect} providers are intentional before freeing either build slot.",
                        evidence="Multiple planned/static providers: " + ", ".join(duplicate_providers),
                        current_state=f"{len(duplicate_providers)} providers",
                        proposed_state="Keep intentional overlap or review one provider for reassignment",
                        confidence="medium",
                        affected_seats=duplicate_providers,
                    )
                )

        for item in self.unique_set_service.evaluate(scope.resolved_builds):
            if item.state != "conditional":
                continue
            if any(
                finding.subject == item.effect_name
                and finding.category == "conditional"
                for finding in findings
            ):
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
                    current_state="Set is equipped; uptime is unproven",
                    proposed_state="Verify trigger ownership and execution",
                    confidence="medium",
                    affected_seats=(item.provider,),
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
        required_reviews = tuple(assignment_reviews[name] for name in required_names)
        covered_count = sum(
            review.state == "assigned_supported" for review in required_reviews
        )
        conditional_count = sum(
            review.state in {"assigned_conditional", "backup_only"}
            for review in required_reviews
        )
        planned_count = sum(
            review.state == "assigned_unproven" for review in required_reviews
        )
        ownership_attention_count = sum(
            review.state == "unassigned_available" for review in required_reviews
        )
        unverified_count = sum(
            review.state == "gap"
            and snapshot.status.get(review.effect_name, "unverified") == "unverified"
            for review in required_reviews
        )
        missing_count = sum(review.state == "gap" for review in required_reviews) - unverified_count
        return RaidPlanAdviserReview(
            plan_id=raid_plan.plan_id,
            plan_name=raid_plan.name,
            trial_id=raid_plan.trial_id,
            resolved_build_count=len(scope.resolved_builds),
            named_member_count=scope.named_members,
            total_chairs=int(total_chairs),
            required_effect_count=len(required_reviews),
            covered_effect_count=covered_count,
            conditional_effect_count=conditional_count,
            planned_unproven_effect_count=planned_count,
            ownership_attention_effect_count=ownership_attention_count,
            missing_effect_count=missing_count,
            unverified_effect_count=unverified_count,
            findings=ordered,
        )


__all__ = [
    "RaidPlanAdviserFinding",
    "RaidPlanAdviserReview",
    "RaidPlanOptimizerAdviserService",
]
