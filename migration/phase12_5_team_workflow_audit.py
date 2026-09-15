from __future__ import annotations

from dataclasses import dataclass
import json

from models.build_model import BuildRoster
from models.roster_model import RosterMember
from services.generated_roster_plan_service import GeneratedRosterPlan


@dataclass(frozen=True)
class Phase125TeamWorkflowAudit:
    team_name: str
    team_registered: bool
    generated_plan_found: bool
    slot_count: int
    saved_slot_count: int
    recruit_slot_count: int
    exact_saved_assignment_count: int
    adopted_prescription_count: int
    unresolved_count: int
    problems: tuple[str, ...]
    boundaries: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.team_registered and self.generated_plan_found and not self.problems


class Phase125TeamWorkflowAuditService:
    """Audit one persisted Team Workflow Integration result without changing it.

    Phase 12.5 owns durable identity and assignment integrity, not encounter
    outcome. Recruit/open chairs and unresolved encounter-facing build details are
    therefore counted and preserved as boundaries rather than treated as failures.
    Contradictory or lost identity, missing exact saved builds, duplicate chairs,
    and lost recruit-prescription evidence are failures.
    """

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _identity_values(cls, value) -> set[str]:
        return {
            text.casefold()
            for text in (
                cls._clean(getattr(value, "PlayerName", "")),
                cls._clean(getattr(value, "CharacterName", "")),
                cls._clean(getattr(value, "Name", "")),
                cls._clean(getattr(value, "Gamertag", "")),
            )
            if text
        }

    @classmethod
    def _team_names(cls, member: RosterMember) -> set[str]:
        return {
            cls._clean(value).casefold()
            for value in str(getattr(member, "Team", "") or "").split(",")
            if cls._clean(value)
        }

    @classmethod
    def _find_saved_build(cls, roster: BuildRoster, slot):
        wanted_people = {
            cls._clean(slot.player_name).casefold(),
            cls._clean(slot.character_name).casefold(),
        }
        wanted_people.discard("")
        wanted_build = cls._clean(slot.build_name).casefold()
        for build in roster.Members:
            if wanted_people and not (cls._identity_values(build) & wanted_people):
                continue
            if wanted_build and cls._clean(getattr(build, "BuildName", "")).casefold() != wanted_build:
                continue
            return build
        return None

    @classmethod
    def _find_roster_member(cls, members: tuple[RosterMember, ...], slot):
        wanted = {
            cls._clean(slot.player_name).casefold(),
            cls._clean(slot.character_name).casefold(),
        }
        wanted.discard("")
        for member in members:
            if wanted and cls._identity_values(member) & wanted:
                return member
        return None

    @classmethod
    def audit(
        cls,
        *,
        team_name: str,
        registered_team_names: tuple[str, ...],
        plan: GeneratedRosterPlan | None,
        builds: BuildRoster,
        roster_members: tuple[RosterMember, ...],
        recruit_prescriptions: dict[str, dict[str, object]] | None = None,
    ) -> Phase125TeamWorkflowAudit:
        name = cls._clean(team_name)
        registered = {cls._clean(value).casefold() for value in registered_team_names}
        team_registered = bool(name) and name.casefold() in registered
        problems: list[str] = []
        boundaries: list[str] = []
        prescriptions = {
            cls._clean(key).casefold(): value
            for key, value in (recruit_prescriptions or {}).items()
            if cls._clean(key) and isinstance(value, dict)
        }

        if not name:
            problems.append("Team name is empty.")
        elif not team_registered:
            problems.append(f"Roster team identity is missing: {name}")

        if plan is None:
            problems.append(f"Generated plan is missing for team: {name or '<unnamed>'}")
            return Phase125TeamWorkflowAudit(
                team_name=name,
                team_registered=team_registered,
                generated_plan_found=False,
                slot_count=0,
                saved_slot_count=0,
                recruit_slot_count=0,
                exact_saved_assignment_count=0,
                adopted_prescription_count=0,
                unresolved_count=0,
                problems=tuple(problems),
                boundaries=(),
            )

        if cls._clean(plan.name).casefold() != name.casefold():
            problems.append(
                f"Generated plan identity mismatch: expected {name!r}, found {plan.name!r}."
            )

        seen_slots: set[str] = set()
        saved_count = recruit_count = exact_count = adopted_count = unresolved_count = 0

        for slot in plan.slots:
            slot_name = cls._clean(slot.slot_name)
            slot_key = slot_name.casefold()
            if not slot_name:
                problems.append("Generated plan contains an unnamed chair.")
                continue
            if slot_key in seen_slots:
                problems.append(f"Duplicate generated chair: {slot_name}")
            seen_slots.add(slot_key)

            if cls._clean(slot.unresolved):
                unresolved_count += 1

            if slot.kind != "saved":
                recruit_count += 1
                if cls._clean(slot.player_name).casefold() not in {"", "recruitment needed"}:
                    problems.append(
                        f"Recruit chair {slot_name} has a real player name but is not persisted as a saved assignment."
                    )
                boundaries.append(
                    f"{slot_name}: recruit/open chair remains explicit and contributes no canonical saved build until adopted."
                )
                continue

            saved_count += 1
            build = cls._find_saved_build(builds, slot)
            if build is None:
                problems.append(
                    f"{slot_name}: exact saved assignment cannot be resolved: "
                    f"{cls._clean(slot.player_name)} / {cls._clean(slot.build_name)}"
                )
                continue
            exact_count += 1

            slot_class = cls._clean(slot.eso_class)
            build_class = cls._clean(getattr(build, "EsoClass", ""))
            if slot_class and slot_class.casefold() not in {"any class", build_class.casefold()}:
                problems.append(
                    f"{slot_name}: assignment class mismatch: plan={slot_class!r}, build={build_class!r}."
                )

            member = cls._find_roster_member(roster_members, slot)
            if member is None:
                problems.append(
                    f"{slot_name}: assigned saved player is missing from Roster: {cls._clean(slot.player_name)}"
                )
            elif name.casefold() not in cls._team_names(member):
                problems.append(
                    f"{slot_name}: assigned player is not a member of named team {name!r}: "
                    f"{cls._clean(slot.player_name)}"
                )

            evidence = prescriptions.get(slot_key)
            if evidence is not None:
                adopted_count += 1
                required = {
                    "slot_name",
                    "role",
                    "eso_class",
                    "build_name",
                    "source_kind",
                    "source_name",
                    "source_url",
                    "candidate_id",
                    "gear_sets",
                    "skills",
                    "mundus",
                    "unresolved",
                }
                missing = sorted(required - set(evidence))
                if missing:
                    problems.append(
                        f"{slot_name}: adopted recruit prescription lost structured field(s): {', '.join(missing)}"
                    )
                else:
                    boundaries.append(
                        f"{slot_name}: original recruit prescription is preserved separately from the adopted canonical build for later encounter evaluation."
                    )

        if unresolved_count:
            boundaries.append(
                f"{unresolved_count} assignment(s) retain explicit unresolved evidence; Phase 12.5 does not convert it to encounter-safe truth."
            )
        boundaries.append(
            "Encounter compliance, phase-specific loadouts, rotation timing, uptime, sustain-through-rotation, and raid outcome remain later-phase responsibilities."
        )

        return Phase125TeamWorkflowAudit(
            team_name=name,
            team_registered=team_registered,
            generated_plan_found=True,
            slot_count=len(plan.slots),
            saved_slot_count=saved_count,
            recruit_slot_count=recruit_count,
            exact_saved_assignment_count=exact_count,
            adopted_prescription_count=adopted_count,
            unresolved_count=unresolved_count,
            problems=tuple(dict.fromkeys(problems)),
            boundaries=tuple(dict.fromkeys(boundaries)),
        )


def recruit_prescriptions_from_rows(rows) -> dict[str, dict[str, object]]:
    """Decode sidecar rows selected by the CLI/audit caller."""

    result: dict[str, dict[str, object]] = {}
    for row in rows:
        slot_name = str(row["slot_name"] or "").strip()
        if not slot_name:
            continue
        try:
            payload = json.loads(str(row["prescription_json"] or "{}"))
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            result[slot_name] = payload
    return result
