from __future__ import annotations

"""Compose persisted Raid Plan evidence for the Readiness surface.

Readiness is a presentation consumer. Build resolution remains owned by the canonical
saved-build resolver, while Coverage remains owned by the existing static/planned
coverage services. This service only turns those results into per-chair readiness
labels without inventing runtime uptime.
"""

from dataclasses import dataclass
from pathlib import Path

from models.raid_plan import RaidPlan, RaidPlanMember
from services.build_service import BuildService
from services.raid_group_effect_catalog import GROUP_COVERAGE_NAMES
from services.raid_named_group_effect_capability_service import (
    RaidNamedGroupEffectCapabilityService,
)
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
from services.saved_build_capability_service import (
    RaidCoverageSnapshot,
    SavedBuildCapabilityService,
    summarize_raid_coverage,
)
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE


COVERAGE_EFFECT_NAMES = tuple(
    dict.fromkeys((*GROUP_COVERAGE_NAMES, *UNIQUE_SUPPORT_SET_NAMES))
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _effect_key(value: object) -> str:
    return _clean(value).casefold()


def _extend_snapshot(snapshot: RaidCoverageSnapshot) -> RaidCoverageSnapshot:
    status = {name: "unverified" for name in COVERAGE_EFFECT_NAMES}
    providers = {name: [] for name in COVERAGE_EFFECT_NAMES}
    conditional = {name: [] for name in COVERAGE_EFFECT_NAMES}
    for name in COVERAGE_EFFECT_NAMES:
        if name in snapshot.status:
            status[name] = snapshot.status[name]
        if name in snapshot.providers:
            providers[name] = list(snapshot.providers[name])
        if name in snapshot.conditional_providers:
            conditional[name] = list(snapshot.conditional_providers[name])
    return RaidCoverageSnapshot(status, providers, conditional)


@dataclass(frozen=True)
class RaidReadinessSeatEvidence:
    seat_id: str
    build_state: str
    build_label: str
    build_detail: str
    coverage_state: str
    coverage_label: str
    coverage_detail: str


@dataclass(frozen=True)
class RaidReadinessEvidence:
    seats: tuple[RaidReadinessSeatEvidence, ...]

    def seat(self, seat_id: str) -> RaidReadinessSeatEvidence | None:
        wanted = _effect_key(seat_id)
        return next(
            (row for row in self.seats if _effect_key(row.seat_id) == wanted),
            None,
        )


class RaidReadinessEvidenceService:
    def __init__(self, *, data_dir: Path, database_path: Path) -> None:
        self.data_dir = Path(data_dir)
        self.database_path = Path(database_path)
        self.build_service = BuildService(self.data_dir / "builds.json")
        self.capability_service = SavedBuildCapabilityService(
            self.build_service,
            self.database_path,
        )

    @staticmethod
    def _planned_build(member: RaidPlanMember) -> bool:
        return bool(
            tuple(member.planned_gear_sets or ())
            or tuple(member.planned_skills or ())
            or _clean(member.planned_mundus)
        )

    @staticmethod
    def _assigned_coverage_effects(member: RaidPlanMember) -> tuple[str, ...]:
        display_by_key = {_effect_key(name): name for name in COVERAGE_EFFECT_NAMES}
        result: list[str] = []
        for value in (member.primary_assignment, member.secondary_assignment):
            display = display_by_key.get(_effect_key(value))
            if display and display not in result:
                result.append(display)
        return tuple(result)

    def _snapshot(self, scope) -> RaidCoverageSnapshot:
        audits = [
            (row.build, self.capability_service.audit_build(row.build))
            for row in scope.members
        ]
        snapshot = _extend_snapshot(
            summarize_raid_coverage(DEFAULT_RAID_COVERAGE_PROFILE, audits)
        )
        snapshot = RaidNamedGroupEffectCapabilityService().overlay(
            snapshot,
            scope.resolved_builds,
            capability_service=self.capability_service,
        )
        snapshot = RaidUniqueSupportSetCapabilityService().overlay(
            snapshot,
            scope.resolved_builds,
        )
        snapshot = RaidPlannedGearCoverageService(self.database_path).overlay(
            snapshot,
            tuple(
                PlannedGearCoverageProvider(
                    seat_id=row.seat_id,
                    provider_label=row.player_label,
                    gear_sets=row.gear_sets,
                )
                for row in scope.planned_gear
            ),
            effect_names=COVERAGE_EFFECT_NAMES,
        )
        snapshot = RaidPlannedSkillCoverageService(self.database_path).overlay(
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
            effect_names=COVERAGE_EFFECT_NAMES,
        )
        return snapshot

    def evaluate(self, plan: RaidPlan) -> RaidReadinessEvidence:
        saved_builds = tuple(self.build_service.load().Members)
        scope = RaidPlanCoverageScopeService().compose(
            raid_plan=plan,
            saved_builds=saved_builds,
            coverage_effect_names=COVERAGE_EFFECT_NAMES,
            total_chairs=len(plan.members),
        )
        snapshot = self._snapshot(scope)
        resolved_seats = {row.seat_id.casefold() for row in scope.members}
        assignment_service = RaidPlanCoverageAssignmentService()

        rows: list[RaidReadinessSeatEvidence] = []
        for member in plan.members:
            selected = member.build_selected
            planned = self._planned_build(member)
            resolved = member.seat_id.casefold() in resolved_seats

            if selected and resolved:
                build_state = "ready"
                build_label = "✓ READY"
                build_detail = _clean(member.selected_build_name) or "Selected build resolved"
            elif selected:
                build_state = "gap"
                build_label = "! GAP"
                build_detail = "Selected build reference did not resolve"
            elif planned:
                build_state = "planned"
                build_label = "◐ PLANNED"
                build_detail = "Comp Maker planning evidence saved; full build not selected"
            else:
                build_state = "gap"
                build_label = "! GAP"
                build_detail = "Build not selected"

            effect_names = self._assigned_coverage_effects(member)
            if not effect_names:
                coverage_state = "not_applicable"
                coverage_label = "— NO DUTY"
                coverage_detail = "No named Coverage effect is assigned to this chair"
            else:
                reviews = tuple(
                    assignment_service.review(
                        effect_name=effect_name,
                        scope=scope,
                        snapshot=snapshot,
                    )
                    for effect_name in effect_names
                )
                missing = tuple(
                    review.effect_name
                    for review in reviews
                    if not review.counts_as_planned_coverage
                )
                if missing:
                    coverage_state = "gap"
                    coverage_label = "! GAP"
                    coverage_detail = "Missing: " + ", ".join(missing)
                else:
                    coverage_state = "covered"
                    coverage_label = "✓ COVERED"
                    coverage_detail = "; ".join(
                        f"{review.effect_name}: {review.label}"
                        for review in reviews
                    )

            rows.append(
                RaidReadinessSeatEvidence(
                    seat_id=member.seat_id,
                    build_state=build_state,
                    build_label=build_label,
                    build_detail=build_detail,
                    coverage_state=coverage_state,
                    coverage_label=coverage_label,
                    coverage_detail=coverage_detail,
                )
            )

        return RaidReadinessEvidence(seats=tuple(rows))


__all__ = [
    "COVERAGE_EFFECT_NAMES",
    "RaidReadinessSeatEvidence",
    "RaidReadinessEvidence",
    "RaidReadinessEvidenceService",
]
