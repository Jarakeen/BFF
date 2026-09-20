from __future__ import annotations

"""Framework-neutral FoundryDock projections for Discord delivery.

Discord is a presentation surface only. Raid Plans, Personnel, team schedules,
encounter evidence, and user-owned raid maps remain authoritative in their
existing FoundryDock services/stores.
"""

from dataclasses import dataclass
from pathlib import Path

from models.raid_plan import RaidPlan, RaidPlanMember
from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)
from services.encounter_raid_map_store import EncounterRaidMapStore
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


@dataclass(frozen=True, slots=True)
class DiscordRaidMemberBrief:
    seat_id: str
    player: str
    role: str
    eso_class: str
    build: str
    gear_sets: tuple[str, ...]
    assignments: tuple[str, ...]
    notes: str


@dataclass(frozen=True, slots=True)
class DiscordRaidBrief:
    plan_id: str
    name: str
    trial_id: str
    difficulty: str
    team_name: str
    plan_note: str
    members: tuple[DiscordRaidMemberBrief, ...]


@dataclass(frozen=True, slots=True)
class DiscordBuildBrief:
    plan_id: str
    plan_name: str
    seat_id: str
    player: str
    character: str
    role: str
    eso_class: str
    build: str
    gear_sets: tuple[str, ...]
    skills: tuple[str, ...]
    mundus: str
    assignments: tuple[str, ...]
    notes: str


@dataclass(frozen=True, slots=True)
class DiscordStrategyBrief:
    encounter_id: str
    encounter_name: str
    callouts: tuple[str, ...]
    strategy_rows: tuple[tuple[str, str, str], ...]
    role_impact: tuple[str, ...]
    timeline: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True, slots=True)
class DiscordRaidMapBrief:
    map_id: str
    encounter_id: str
    label: str
    path: Path


class FoundryDockDiscordCompanionService:
    """Read FoundryDock-owned state and project it into Discord-safe briefs."""

    def __init__(
        self,
        *,
        plan_repository: RaidPlanRepository,
        roster_service: RosterService,
        data_dir: Path,
    ) -> None:
        self.plan_repository = plan_repository
        self.roster_service = roster_service
        self.data_dir = Path(data_dir)
        self.strategy_service = EncounterGuideEvidenceProjectionService(self.data_dir)
        self.map_store = EncounterRaidMapStore(self.data_dir)

    def list_plans(self) -> tuple[RaidPlan, ...]:
        return self.plan_repository.list_plans()

    def resolve_plan(self, plan_ref: str = "") -> RaidPlan:
        wanted = _clean(plan_ref).casefold()
        plans = self.list_plans()
        if not plans:
            raise LookupError("FoundryDock has no saved Raid Plans.")

        if wanted:
            exact = tuple(
                plan
                for plan in plans
                if plan.plan_id.casefold() == wanted or plan.name.casefold() == wanted
            )
            if len(exact) == 1:
                return exact[0]
            if len(exact) > 1:
                raise LookupError(f"More than one Raid Plan matches {plan_ref!r}.")

        active = tuple(plan for plan in plans if plan.status == "active")
        if not wanted and len(active) == 1:
            return active[0]
        if not wanted and len(plans) == 1:
            return plans[0]

        raise LookupError(
            "Raid Plan is ambiguous. Use the saved plan name or stable plan id."
        )

    def active_plan_for_team(self, team_name: str) -> RaidPlan | None:
        wanted = _clean(team_name).casefold()
        if not wanted:
            return None
        matches = tuple(
            plan
            for plan in self.list_plans()
            if _clean(plan.team_name).casefold() == wanted and plan.status == "active"
        )
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def _member_assignments(member: RaidPlanMember) -> tuple[str, ...]:
        values = (
            member.primary_assignment,
            member.secondary_assignment,
            *member.utility_assignments,
        )
        return tuple(dict.fromkeys(_clean(value) for value in values if _clean(value)))

    @classmethod
    def _raid_member_brief(cls, member: RaidPlanMember) -> DiscordRaidMemberBrief:
        build = _clean(member.selected_build_name)
        if not build and member.planned_gear_sets:
            build = " + ".join(member.planned_gear_sets)
        return DiscordRaidMemberBrief(
            seat_id=member.seat_id,
            player=_clean(member.gamertag) or "Recruitment Needed",
            role=_clean(member.role),
            eso_class=_clean(member.eso_class),
            build=build,
            gear_sets=tuple(member.planned_gear_sets),
            assignments=cls._member_assignments(member),
            notes=_clean(member.notes),
        )

    def raid_brief(self, plan_ref: str = "") -> DiscordRaidBrief:
        plan = self.resolve_plan(plan_ref)
        return DiscordRaidBrief(
            plan_id=plan.plan_id,
            name=plan.name,
            trial_id=plan.trial_id,
            difficulty=_clean(plan.difficulty),
            team_name=_clean(plan.team_name),
            plan_note=_clean(plan.plan_note),
            members=tuple(self._raid_member_brief(member) for member in plan.members),
        )

    def _discord_aliases(self, member: RaidPlanMember) -> tuple[str, ...]:
        aliases = {_clean(member.gamertag).casefold(), member.seat_id.casefold()}
        if member.roster_member_id:
            roster = self.roster_service.get_member(member.roster_member_id)
            if roster is not None:
                aliases.update(
                    {
                        _clean(roster.PlayerName).casefold(),
                        _clean(roster.DiscordName).casefold(),
                    }
                )
        return tuple(alias for alias in aliases if alias)

    def build_brief(self, *, plan_ref: str = "", player_ref: str) -> DiscordBuildBrief:
        plan = self.resolve_plan(plan_ref)
        wanted = _clean(player_ref).casefold()
        if not wanted:
            raise LookupError("Player, Discord name, or seat is required.")

        matches = tuple(
            member
            for member in plan.members
            if wanted in self._discord_aliases(member)
        )
        if len(matches) != 1:
            raise LookupError(
                f"Could not uniquely match {player_ref!r} to one chair in {plan.name}."
            )

        member = matches[0]
        build = _clean(member.selected_build_name)
        if not build and member.planned_gear_sets:
            build = " + ".join(member.planned_gear_sets)
        return DiscordBuildBrief(
            plan_id=plan.plan_id,
            plan_name=plan.name,
            seat_id=member.seat_id,
            player=_clean(member.gamertag) or member.seat_id,
            character=_clean(member.character_name),
            role=_clean(member.role),
            eso_class=_clean(member.eso_class),
            build=build,
            gear_sets=tuple(member.planned_gear_sets),
            skills=tuple(member.planned_skills),
            mundus=_clean(member.planned_mundus),
            assignments=self._member_assignments(member),
            notes=_clean(member.notes),
        )

    def strategy_brief(
        self,
        *,
        encounter_id: str,
        encounter_name: str = "",
    ) -> DiscordStrategyBrief:
        projection = self.strategy_service.get(
            _clean(encounter_id),
            encounter_name=_clean(encounter_name),
        )
        return DiscordStrategyBrief(
            encounter_id=projection.encounter_id,
            encounter_name=projection.encounter_name,
            callouts=tuple(projection.callouts),
            strategy_rows=tuple(
                (row.mechanic, row.summary, row.mitigation)
                for row in projection.strategy
            ),
            role_impact=tuple(projection.role_impact),
            timeline=tuple(
                (row.marker, row.label, row.detail)
                for row in projection.timeline
            ),
        )

    def raid_maps(self, encounter_id: str) -> tuple[DiscordRaidMapBrief, ...]:
        maps = self.map_store.list_maps(_clean(encounter_id))
        return tuple(
            DiscordRaidMapBrief(
                map_id=row.map_id,
                encounter_id=row.encounter_id,
                label=row.label,
                path=self.map_store.resolve_path(row),
            )
            for row in maps
        )

    def team_schedule_text(self, team_name: str) -> str:
        schedule = self.roster_service.get_team_schedule(team_name)
        return schedule.display_text if schedule is not None else "Schedule not set"


__all__ = [
    "DiscordBuildBrief",
    "DiscordRaidBrief",
    "DiscordRaidMapBrief",
    "DiscordRaidMemberBrief",
    "DiscordStrategyBrief",
    "FoundryDockDiscordCompanionService",
]
