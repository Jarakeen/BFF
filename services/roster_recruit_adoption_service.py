from __future__ import annotations

from dataclasses import asdict
import json

from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.generated_roster_plan_service import (
    GeneratedRosterPlan,
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
from services.roster_service import RosterService
from services.team_prescription_slot_constraints import build_gear_set_names


class RosterRecruitAdoptionService:
    """Replace a generated recruit chair with a real roster member/build.

    The generated-team assignment and canonical Build remain separate concepts.
    The original recruit prescription is persisted as structured evidence before a
    real player is attached, so later encounter-aware evaluation can compare the
    assigned build with the prescription instead of reconstructing intent from UI
    text.
    """

    def __init__(
        self,
        *,
        builds: BuildService,
        plans: GeneratedRosterPlanService,
        roster: RosterService,
    ) -> None:
        self.builds = builds
        self.plans = plans
        self.roster = roster
        self.db = plans.db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_roster_recruit_prescription (
                plan_id INTEGER NOT NULL
                    REFERENCES generated_roster_plan(id)
                    ON DELETE CASCADE,
                slot_name TEXT NOT NULL,
                prescription_json TEXT NOT NULL,
                adopted_player_name TEXT NOT NULL DEFAULT '',
                adopted_character_name TEXT NOT NULL DEFAULT '',
                adopted_build_name TEXT NOT NULL DEFAULT '',
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

    def _member(self, member_id: int):
        member = self.roster.get_member(int(member_id))
        if member is None:
            raise ValueError(f"Roster member {member_id} does not exist.")
        return member

    def _slot(self, plan: GeneratedRosterPlan, slot_name: str) -> GeneratedRosterPlanSlot:
        wanted = self._clean(slot_name).casefold()
        slot = next(
            (
                item
                for item in plan.slots
                if self._clean(item.slot_name).casefold() == wanted
            ),
            None,
        )
        if slot is None:
            raise ValueError(f"Generated team has no chair named {slot_name!r}.")
        if slot.kind == "saved":
            raise ValueError(f"{slot.slot_name} already has a saved player/build assignment.")
        return slot

    def available_builds(self, member_id: int) -> tuple[PlayerBuild, ...]:
        member = self._member(member_id)
        wanted = self._identity_values(member)
        roster = self.builds.load()
        matches = [
            build
            for build in roster.Members
            if wanted and self._identity_values(build) & wanted
        ]
        return tuple(
            sorted(
                matches,
                key=lambda build: (
                    self._clean(getattr(build, "BuildName", "")).casefold(),
                    self._clean(getattr(build, "Name", "")).casefold(),
                ),
            )
        )

    def _find_build(self, member_id: int, build_name: str) -> PlayerBuild:
        wanted = self._clean(build_name).casefold()
        for build in self.available_builds(member_id):
            if self._clean(getattr(build, "BuildName", "")).casefold() == wanted:
                return build
        raise ValueError(f"Roster member has no saved build named {build_name!r}.")

    @staticmethod
    def _dedupe(values) -> tuple[str, ...]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value or "").strip()
            key = text.casefold()
            if not text or key in seen:
                continue
            seen.add(key)
            result.append(text)
        return tuple(result)

    @classmethod
    def _build_skills(cls, build: PlayerBuild) -> tuple[str, ...]:
        return cls._dedupe((*build.FrontBarSkills, *build.BackBarSkills))

    @classmethod
    def _prescription_payload(cls, slot: GeneratedRosterPlanSlot) -> dict[str, object]:
        return {
            "slot_name": slot.slot_name,
            "role": slot.role,
            "eso_class": slot.eso_class,
            "build_name": slot.build_name,
            "source_kind": slot.source_kind,
            "source_name": slot.source_name,
            "source_url": slot.source_url,
            "candidate_id": slot.candidate_id,
            "gear_sets": list(slot.gear_sets),
            "skills": list(slot.skills),
            "mundus": slot.mundus,
            "unresolved": slot.unresolved,
        }

    def prescription_evidence(
        self, plan_name: str, slot_name: str
    ) -> dict[str, object] | None:
        plan = self.plans.load_plan(plan_name)
        if plan is None:
            return None
        row = self.db.execute(
            """
            SELECT prescription_json
            FROM generated_roster_recruit_prescription
            WHERE plan_id = ? AND slot_name = ? COLLATE NOCASE
            """,
            (plan.plan_id, self._clean(slot_name)),
        ).fetchone()
        if row is None:
            return None
        try:
            value = json.loads(str(row["prescription_json"] or "{}"))
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    def _remember_prescription(
        self,
        *,
        plan: GeneratedRosterPlan,
        slot: GeneratedRosterPlanSlot,
        player_name: str,
        character_name: str,
        build_name: str,
    ) -> None:
        existing = self.db.execute(
            """
            SELECT 1
            FROM generated_roster_recruit_prescription
            WHERE plan_id = ? AND slot_name = ? COLLATE NOCASE
            """,
            (plan.plan_id, slot.slot_name),
        ).fetchone()
        payload = json.dumps(
            self._prescription_payload(slot), ensure_ascii=False, sort_keys=True
        )
        if existing is None:
            self.db.execute(
                """
                INSERT INTO generated_roster_recruit_prescription (
                    plan_id, slot_name, prescription_json,
                    adopted_player_name, adopted_character_name, adopted_build_name,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    plan.plan_id,
                    slot.slot_name,
                    payload,
                    player_name,
                    character_name,
                    build_name,
                ),
            )
        else:
            # Preserve the original prescription JSON. Only adopted identity changes
            # on later reassignment.
            self.db.execute(
                """
                UPDATE generated_roster_recruit_prescription
                SET adopted_player_name = ?, adopted_character_name = ?,
                    adopted_build_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE plan_id = ? AND slot_name = ? COLLATE NOCASE
                """,
                (
                    player_name,
                    character_name,
                    build_name,
                    plan.plan_id,
                    slot.slot_name,
                ),
            )
        self.db.commit()

    def _add_member_to_team(self, member, team_name: str) -> None:
        teams = [part.strip() for part in str(member.Team or "").split(",") if part.strip()]
        if team_name.casefold() not in {name.casefold() for name in teams}:
            teams.append(team_name)
        member.Team = ", ".join(teams)
        self.roster.update_member(member)

    def _saved_slot(
        self,
        original: GeneratedRosterPlanSlot,
        member,
        build: PlayerBuild,
        *,
        unresolved_suffix: str = "",
    ) -> GeneratedRosterPlanSlot:
        player_name = self._clean(member.PlayerName) or self._clean(build.Name) or "Assigned Player"
        character_name = self._clean(member.CharacterName) or self._clean(build.Name)
        unresolved = self._dedupe((original.unresolved, unresolved_suffix))
        return GeneratedRosterPlanSlot(
            slot_name=original.slot_name,
            kind="saved",
            player_name=player_name,
            character_name=character_name,
            eso_class=self._clean(build.EsoClass) or self._clean(original.eso_class),
            build_name=self._clean(build.BuildName) or "Current Build",
            gear_summary=" + ".join(build_gear_set_names(build)),
            unresolved="; ".join(unresolved),
            role=self._clean(build.Role) or self._clean(original.role),
            source_kind="saved_build",
            source_name=character_name or player_name,
            source_url="",
            candidate_id=f"saved:{player_name.casefold()}:{self._clean(build.BuildName).casefold()}",
            gear_sets=tuple(build_gear_set_names(build)),
            skills=self._build_skills(build),
            mundus=self._clean(build.Mundus),
        )

    def _replace_slot(
        self,
        plan: GeneratedRosterPlan,
        original: GeneratedRosterPlanSlot,
        replacement: GeneratedRosterPlanSlot,
    ) -> GeneratedRosterPlan:
        slots = tuple(
            replacement if item.slot_name == original.slot_name else item
            for item in plan.slots
        )
        return self.plans.save_plan(
            name=plan.name,
            goal=plan.goal,
            difficulty=plan.difficulty,
            slots=slots,
        )

    def assign_existing_build(
        self,
        *,
        plan_name: str,
        slot_name: str,
        member_id: int,
        build_name: str,
    ) -> GeneratedRosterPlan:
        plan = self.plans.load_plan(plan_name)
        if plan is None:
            raise ValueError(f"Generated team {plan_name!r} does not exist.")
        slot = self._slot(plan, slot_name)
        member = self._member(member_id)
        build = self._find_build(member_id, build_name)
        required_class = self._clean(slot.eso_class)
        if required_class and required_class.casefold() != "any class":
            if self._clean(build.EsoClass).casefold() != required_class.casefold():
                raise ValueError(
                    f"{build.BuildName or 'Saved build'} is {build.EsoClass or 'class unresolved'}, "
                    f"but {slot.slot_name} requires {required_class}."
                )
        replacement = self._saved_slot(slot, member, build)
        self._remember_prescription(
            plan=plan,
            slot=slot,
            player_name=replacement.player_name,
            character_name=replacement.character_name,
            build_name=replacement.build_name,
        )
        self._add_member_to_team(member, plan.name)
        return self._replace_slot(plan, slot, replacement)

    def adopt_prescribed_setup(
        self,
        *,
        plan_name: str,
        slot_name: str,
        member_id: int,
        base_build_name: str,
        new_build_name: str,
    ) -> GeneratedRosterPlan:
        plan = self.plans.load_plan(plan_name)
        if plan is None:
            raise ValueError(f"Generated team {plan_name!r} does not exist.")
        slot = self._slot(plan, slot_name)
        member = self._member(member_id)
        base = self._find_build(member_id, base_build_name)
        new_name = self._clean(new_build_name)
        if not new_name:
            raise ValueError("A new build name is required when adopting a prescription.")
        for existing in self.available_builds(member_id):
            if self._clean(existing.BuildName).casefold() == new_name.casefold():
                raise ValueError(f"This character already has a build named {new_name!r}.")

        required_class = self._clean(slot.eso_class)
        if required_class and required_class.casefold() != "any class":
            if self._clean(base.EsoClass).casefold() != required_class.casefold():
                raise ValueError(
                    f"Cannot adopt this prescription onto {base.EsoClass or 'an unresolved class'}; "
                    f"the chair requires {required_class}."
                )

        adopted = PlayerBuild.from_dict(base.to_dict())
        adopted.BuildName = new_name
        if self._clean(slot.role):
            adopted.Role = self._clean(slot.role)
        if self._clean(slot.mundus):
            adopted.Mundus = self._clean(slot.mundus)

        roster = self.builds.load()
        roster.Members.append(adopted)
        self.builds.save(roster)

        boundary = (
            "Adopted from recruit prescription using a real saved build as the base. "
            "Prescribed gear-set and ability lists remain structured assignment evidence; "
            "exact gear slots, traits, enchants, and skill-bar placement were not invented."
        )
        replacement = self._saved_slot(
            slot,
            member,
            adopted,
            unresolved_suffix=boundary,
        )
        self._remember_prescription(
            plan=plan,
            slot=slot,
            player_name=replacement.player_name,
            character_name=replacement.character_name,
            build_name=replacement.build_name,
        )
        self._add_member_to_team(member, plan.name)
        return self._replace_slot(plan, slot, replacement)
