from __future__ import annotations

from dataclasses import dataclass
import json

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
    def normalizable_slots(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.ambiguous_slots, *self.blocked_source_slots)))

    @property
    def has_repairs(self) -> bool:
        return (
            self.team_identity_missing
            or bool(self.promotable_slots)
            or bool(self.normalizable_slots)
        )


class Phase125LegacyPlanRepairService:
    """Repair only provable pre-Phase-12.5 generated-plan inconsistencies.

    Missing Roster team identity is safe to backfill because a persisted generated
    plan now canonically owns that user-facing team identity. A legacy recruit chair
    may be promoted to ``saved`` only when its real player/character identity and
    exact saved build resolve uniquely and the source does not identify non-roster
    evidence such as ESO Logs or a reference template.

    A real player name on a recruit chair that cannot be promoted is still invalid
    canonical ownership. Those rows are normalized back to ``Recruitment Needed``
    while their original identity/source payload is preserved in a dedicated legacy
    evidence sidecar. This removes the contradiction without inventing an assignment
    and keeps the historical clue available for later encounter-aware review.
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
        self.db = plans.db
        self._ensure_evidence_schema()

    def _ensure_evidence_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_roster_legacy_assignment_evidence (
                plan_id INTEGER NOT NULL
                    REFERENCES generated_roster_plan(id)
                    ON DELETE CASCADE,
                slot_name TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (plan_id, slot_name)
            )
            """
        )
        self.db.commit()

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

    @staticmethod
    def _slot_payload(slot: GeneratedRosterPlanSlot) -> dict[str, object]:
        return {
            "slot_name": slot.slot_name,
            "kind": slot.kind,
            "player_name": slot.player_name,
            "character_name": slot.character_name,
            "eso_class": slot.eso_class,
            "build_name": slot.build_name,
            "role": slot.role,
            "source_kind": slot.source_kind,
            "source_name": slot.source_name,
            "source_url": slot.source_url,
            "candidate_id": slot.candidate_id,
            "gear_sets": list(slot.gear_sets),
            "skills": list(slot.skills),
            "mundus": slot.mundus,
            "unresolved": slot.unresolved,
        }

    def _remember_legacy_evidence(
        self, plan: GeneratedRosterPlan, slot: GeneratedRosterPlanSlot
    ) -> None:
        payload = json.dumps(self._slot_payload(slot), ensure_ascii=False, sort_keys=True)
        self.db.execute(
            """
            INSERT INTO generated_roster_legacy_assignment_evidence (
                plan_id, slot_name, evidence_json, updated_at
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(plan_id, slot_name) DO UPDATE SET
                evidence_json = excluded.evidence_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (plan.plan_id, slot.slot_name, payload),
        )
        self.db.commit()

    def legacy_assignment_evidence(
        self, plan_name: str, slot_name: str
    ) -> dict[str, object] | None:
        plan = self.plans.load_plan(plan_name)
        if plan is None:
            return None
        row = self.db.execute(
            """
            SELECT evidence_json
            FROM generated_roster_legacy_assignment_evidence
            WHERE plan_id = ? AND slot_name = ? COLLATE NOCASE
            """,
            (plan.plan_id, self._clean(slot_name)),
        ).fetchone()
        if row is None:
            return None
        try:
            value = json.loads(str(row["evidence_json"] or "{}"))
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

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

    @staticmethod
    def _normalized_recruit(slot: GeneratedRosterPlanSlot) -> GeneratedRosterPlanSlot:
        return GeneratedRosterPlanSlot(
            slot_name=slot.slot_name,
            kind=slot.kind,
            player_name="Recruitment Needed",
            character_name="",
            eso_class=slot.eso_class,
            build_name=slot.build_name,
            gear_summary=slot.gear_summary,
            unresolved=slot.unresolved,
            role=slot.role,
            source_kind=slot.source_kind,
            source_name=slot.source_name,
            source_url=slot.source_url,
            candidate_id=slot.candidate_id,
            gear_sets=slot.gear_sets,
            skills=slot.skills,
            mundus=slot.mundus,
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
        normalizable = {name.casefold() for name in inspection.normalizable_slots}
        if not promotable and not normalizable:
            return self.plans.load_plan(plan.name) or plan

        updated_slots: list[GeneratedRosterPlanSlot] = []
        for slot in plan.slots:
            slot_key = slot.slot_name.casefold()
            if slot_key in normalizable:
                self._remember_legacy_evidence(plan, slot)
                updated_slots.append(self._normalized_recruit(slot))
                continue
            if slot_key not in promotable:
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
