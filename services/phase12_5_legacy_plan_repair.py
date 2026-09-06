from __future__ import annotations

from dataclasses import dataclass

from models.build_model import BuildRoster
from models.roster_model import RosterMember
from services.generated_roster_plan_service import (
    GeneratedRosterPlan,
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
from services.roster_service import RosterService


@dataclass(frozen=True)
class Phase125LegacyPlanRepair:
    team_name: str
    team_identity_missing: bool
    promotable_slots: tuple[str, ...]
    ambiguous_slots: tuple[str, ...]
    blocked_source_slots: tuple[str, ...]

    @property
    def has_repairs(self) -> bool:
        return self.team_identity_missing or bool(self.promotable_slots)


class Phase125LegacyPlanRepairService:
    """Repair only provable pre-Phase-12.5 generated-plan inconsistencies.

    The service is deliberately conservative. Missing Roster team identity is safe to
    backfill because a persisted generated plan now canonically owns that user-facing
    team identity. A legacy recruit chair may be promoted to ``saved`` only when its
    real player/character identity and exact saved build resolve uniquely and the
    source does not identify non-roster evidence such as ESO Logs or a reference
    template. Ambiguous rows remain untouched.
    """

    _BLOCKED_SOURCE_KINDS = frozenset({"esologs_snapshot", "reference_template"})

    def __init__(
        self,
        *,
        plans: GeneratedRosterPlanService,
        roster: RosterService,
    ) -> None:
        self.plans = plans
        self.roster = roster

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _identity_values(cls, value) -> set[str]:
        values = {
            cls._clean(getattr(value, field, "")).casefold()
            for field in ("PlayerName", "CharacterName", "Name", "Gamertag")
        }
        return {item for item in values if item}

    @classmethod
    def _matching_builds(cls, builds: BuildRoster, slot: GeneratedRosterPlanSlot):
        wanted_people = {
            cls._clean(slot.player_name).casefold(),
            cls._clean(slot.character_name).casefold(),
        }
        wanted_people.discard("")
        wanted_build = cls._clean(slot.build_name).casefold()
        if not wanted_people or not wanted_build:
            return ()
        matches = []
        for build in builds.Members:
            if not (cls._identity_values(build) & wanted_people):
                continue
            if cls._clean(getattr(build, "BuildName", "")).casefold() != wanted_build:
                continue
            matches.append(build)
        return tuple(matches)

    @classmethod
    def _matching_members(cls, members: tuple[RosterMember, ...], slot: GeneratedRosterPlanSlot):
        wanted = {
            cls._clean(slot.player_name).casefold(),
            cls._clean(slot.character_name).casefold(),
        }
        wanted.discard("")
        if not wanted:
            return ()
        return tuple(
            member for member in members if cls._identity_values(member) & wanted
        )

    @classmethod
    def _real_player_recruit(cls, slot: GeneratedRosterPlanSlot) -> bool:
        return (
            slot.kind != "saved"
            and cls._clean(slot.player_name).casefold()
            not in {"", "recruitment needed"}
        )

    @classmethod
    def _team_names(cls, member: RosterMember) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()
        for raw in str(getattr(member, "Team", "") or "").split(","):
            value = cls._clean(raw)
            key = value.casefold()
            if value and key not in seen:
                seen.add(key)
                values.append(value)
        return values

    def inspect(
        self,
        *,
        plan: GeneratedRosterPlan,
        builds: BuildRoster,
        roster_members: tuple[RosterMember, ...],
    ) -> Phase125LegacyPlanRepair:
        registered = {
            self._clean(name).casefold() for name in self.roster.list_team_names()
        }
        missing_identity = self._clean(plan.name).casefold() not in registered
        promotable: list[str] = []
        ambiguous: list[str] = []
        blocked: list[str] = []

        for slot in plan.slots:
            if not self._real_player_recruit(slot):
                continue
            source_kind = self._clean(slot.source_kind).casefold()
            if source_kind in self._BLOCKED_SOURCE_KINDS:
                blocked.append(slot.slot_name)
                continue
            matching_builds = self._matching_builds(builds, slot)
            matching_members = self._matching_members(roster_members, slot)
            if len(matching_builds) == 1 and len(matching_members) == 1:
                promotable.append(slot.slot_name)
            else:
                ambiguous.append(slot.slot_name)

        return Phase125LegacyPlanRepair(
            team_name=plan.name,
            team_identity_missing=missing_identity,
            promotable_slots=tuple(promotable),
            ambiguous_slots=tuple(ambiguous),
            blocked_source_slots=tuple(blocked),
        )

    def apply(
        self,
        *,
        plan: GeneratedRosterPlan,
        builds: BuildRoster,
        roster_members: tuple[RosterMember, ...],
    ) -> GeneratedRosterPlan:
        inspection = self.inspect(
            plan=plan,
            builds=builds,
            roster_members=roster_members,
        )
        if inspection.team_identity_missing:
            self.roster.ensure_team_name(plan.name)

        promotable = {name.casefold() for name in inspection.promotable_slots}
        if not promotable:
            return self.plans.load_plan(plan.name) or plan

        updated_slots: list[GeneratedRosterPlanSlot] = []
        for slot in plan.slots:
            if slot.slot_name.casefold() not in promotable:
                updated_slots.append(slot)
                continue
            build = self._matching_builds(builds, slot)[0]
            member = self._matching_members(roster_members, slot)[0]
            memberships = self._team_names(member)
            if plan.name.casefold() not in {name.casefold() for name in memberships}:
                memberships.append(plan.name)
                member.Team = ", ".join(memberships)
                self.roster.update_member(member)

            updated_slots.append(
                GeneratedRosterPlanSlot(
                    slot_name=slot.slot_name,
                    kind="saved",
                    player_name=slot.player_name,
                    character_name=(
                        self._clean(getattr(build, "Name", ""))
                        or self._clean(slot.character_name)
                    ),
                    eso_class=self._clean(getattr(build, "EsoClass", "")) or slot.eso_class,
                    build_name=self._clean(getattr(build, "BuildName", "")) or slot.build_name,
                    gear_summary=slot.gear_summary,
                    unresolved=slot.unresolved,
                    role=slot.role,
                    source_kind=slot.source_kind or "saved_build",
                    source_name=slot.source_name or slot.player_name,
                    source_url=slot.source_url,
                    candidate_id=slot.candidate_id,
                    gear_sets=slot.gear_sets,
                    skills=slot.skills,
                    mundus=slot.mundus,
                )
            )

        return self.plans.save_plan(
            name=plan.name,
            goal=plan.goal,
            difficulty=plan.difficulty,
            slots=tuple(updated_slots),
        )
