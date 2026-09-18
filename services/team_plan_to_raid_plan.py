from __future__ import annotations

"""Project generated team evidence into one durable Raid Plan.

Comp Builder and Optimizer own recommendation/generation work. Raid Plan owns the
trial-specific decision about what this run will actually use. This bridge preserves
per-chair planned build evidence without mutating reusable saved Builds or Roster state.
"""

from models.raid_plan import RaidPlan, RaidPlanMember
from services.generated_roster_draft_service import GeneratedRosterDraftSlot


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _slug(value: object) -> str:
    text = _clean(value).casefold().replace("'", "")
    return "-".join(part for part in text.split() if part) or "raid-plan"


def raid_plan_from_generated_slots(
    *,
    name: str,
    trial_name: str,
    difficulty: str,
    slots: tuple[GeneratedRosterDraftSlot, ...],
    team_name: str | None = None,
) -> RaidPlan:
    """Create one plan snapshot from exact generated chair evidence."""

    trial = _clean(trial_name) or "Unknown Trial"
    plan_name = _clean(name) or f"{trial} Plan"
    members: list[RaidPlanMember] = []

    for slot in tuple(slots or ()):
        player = _clean(slot.player_name) or "Recruitment Needed"
        build_name = _clean(slot.build_name)
        if build_name.casefold() in {
            "open requirement",
            "composition requirement",
        }:
            build_name = ""

        members.append(
            RaidPlanMember(
                seat_id=_slug(slot.slot_name),
                gamertag=player,
                character_name=_clean(slot.character_name) or None,
                role=_clean(slot.role) or _clean(slot.slot_name) or None,
                eso_class=_clean(slot.eso_class) or None,
                selected_build_name=build_name or None,
                build_source_kind=_clean(slot.source_kind) or None,
                build_source_name=_clean(slot.source_name) or None,
                build_source_url=_clean(slot.source_url) or None,
                candidate_id=_clean(slot.candidate_id) or None,
                planned_gear_sets=tuple(slot.gear_sets or ()),
                planned_skills=tuple(slot.skills or ()),
                planned_mundus=_clean(slot.mundus) or None,
                notes=_clean(slot.unresolved) or None,
            )
        )

    return RaidPlan(
        plan_id=f"{_slug(trial)}-{_slug(plan_name)}",
        trial_id=_slug(trial),
        name=plan_name,
        team_name=_clean(team_name) or None,
        difficulty=_clean(difficulty) or None,
        members=tuple(members),
    )


__all__ = ["raid_plan_from_generated_slots"]
