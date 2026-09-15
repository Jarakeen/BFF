from __future__ import annotations

from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.generated_roster_draft_prescription_service import (
    GeneratedRosterDraftPrescriptionService,
)
from services.generated_roster_draft_service import (
    GeneratedRosterDraft,
    GeneratedRosterDraftService,
    GeneratedRosterDraftSlot,
)
from services.roster_service import RosterService
from services.team_prescription_slot_constraints import build_gear_set_names


class RosterRecruitAdoptionService:
    """Adopt a generated draft chair into real Team/build state.

    The generated roster draft preserves composition/recruitment evidence. Canonical
    Build and Team state remain separate authorities; adopting a real player/build updates
    those authorities while the draft keeps the original prescription for comparison.
    RaidPlan remains the owner of trial-specific final selections and assignments.
    """

    def __init__(
        self,
        *,
        builds: BuildService,
        plans: GeneratedRosterDraftService,
        roster: RosterService,
    ) -> None:
        self.builds = builds
        self.plans = plans
        self.roster = roster
        self.db = plans.db
        self.prescriptions = GeneratedRosterDraftPrescriptionService(self.db)

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

    def _slot(self, plan: GeneratedRosterDraft, slot_name: str) -> GeneratedRosterDraftSlot:
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
            raise ValueError(f"Generated draft has no chair named {slot_name!r}.")
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
    def _prescription_payload(cls, slot: GeneratedRosterDraftSlot) -> dict[str, object]:
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
        return self.prescriptions.load(plan.draft_id, self._clean(slot_name))

    def _remember_prescription(
        self,
        *,
        plan: GeneratedRosterDraft,
        slot: GeneratedRosterDraftSlot,
        player_name: str,
        character_name: str,
        build_name: str,
    ) -> None:
        self.prescriptions.save(
            draft_id=plan.draft_id,
            slot_name=slot.slot_name,
            prescription=self._prescription_payload(slot),
            adopted_player_name=player_name,
            adopted_character_name=character_name,
            adopted_build_name=build_name,
        )

    def _add_member_to_team(self, member, team_name: str) -> None:
        teams = [part.strip() for part in str(member.Team or "").split(",") if part.strip()]
        if team_name.casefold() not in {name.casefold() for name in teams}:
            teams.append(team_name)
        member.Team = ", ".join(teams)
        self.roster.update_member(member)

    def _saved_slot(
        self,
        original: GeneratedRosterDraftSlot,
        member,
        build: PlayerBuild,
        *,
        unresolved_suffix: str = "",
    ) -> GeneratedRosterDraftSlot:
        player_name = self._clean(member.PlayerName) or self._clean(build.Name) or "Assigned Player"
        character_name = self._clean(member.CharacterName) or self._clean(build.Name)
        unresolved = self._dedupe((original.unresolved, unresolved_suffix))
        return GeneratedRosterDraftSlot(
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
        plan: GeneratedRosterDraft,
        original: GeneratedRosterDraftSlot,
        replacement: GeneratedRosterDraftSlot,
    ) -> GeneratedRosterDraft:
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
    ) -> GeneratedRosterDraft:
        plan = self.plans.load_plan(plan_name)
        if plan is None:
            raise ValueError(f"Generated draft {plan_name!r} does not exist.")
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
    ) -> GeneratedRosterDraft:
        plan = self.plans.load_plan(plan_name)
        if plan is None:
            raise ValueError(f"Generated draft {plan_name!r} does not exist.")
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
            "Prescribed gear-set and ability lists remain structured draft evidence; "
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
