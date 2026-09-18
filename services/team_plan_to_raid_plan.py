from __future__ import annotations

"""Project generated team evidence into one durable Raid Plan.

Comp Builder and Optimizer own recommendation/generation work. Raid Plan owns the
trial-specific decision about what this run will actually use. This bridge preserves
per-chair planned build evidence without mutating reusable saved Builds or Roster state.
"""

from dataclasses import replace

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
    base_plan: RaidPlan | None = None,
) -> RaidPlan:
    """Create one plan snapshot from exact generated chair evidence."""

    trial = _clean(trial_name) or "Unknown Trial"
    plan_name = _clean(name) or f"{trial} Plan"
    members: list[RaidPlanMember] = []
    base_by_seat = (
        {member.seat_id.casefold(): member for member in base_plan.members}
        if base_plan is not None
        else {}
    )

    for slot in tuple(slots or ()):
        seat_id = _slug(slot.slot_name)
        prior = base_by_seat.get(seat_id.casefold())
        player = _clean(slot.player_name) or (
            prior.gamertag if prior is not None else "Recruitment Needed"
        )
        build_name = _clean(slot.build_name)
        if build_name.casefold() in {
            "open requirement",
            "composition requirement",
        }:
            build_name = ""

        if prior is not None:
            members.append(
                prior.with_selection(
                    gamertag=player,
                    character_name=_clean(slot.character_name) or prior.character_name,
                    role=_clean(slot.role) or prior.role,
                    eso_class=_clean(slot.eso_class) or prior.eso_class,
                    selected_build_name=build_name or prior.selected_build_name,
                    build_source_kind=_clean(slot.source_kind) or prior.build_source_kind,
                    build_source_name=_clean(slot.source_name) or prior.build_source_name,
                    build_source_url=_clean(slot.source_url) or prior.build_source_url,
                    candidate_id=_clean(slot.candidate_id) or prior.candidate_id,
                    planned_gear_sets=tuple(slot.gear_sets or ()) or prior.planned_gear_sets,
                    planned_skills=tuple(slot.skills or ()) or prior.planned_skills,
                    planned_mundus=_clean(slot.mundus) or prior.planned_mundus,
                    notes=_clean(slot.unresolved) or prior.notes,
                )
            )
            continue

        members.append(
            RaidPlanMember(
                seat_id=seat_id,
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

    if base_plan is not None:
        merged = {member.seat_id.casefold(): member for member in base_plan.members}
        for member in members:
            merged[member.seat_id.casefold()] = member
        return replace(
            base_plan,
            name=base_plan.name,
            trial_id=base_plan.trial_id,
            team_name=base_plan.team_name or (_clean(team_name) or None),
            difficulty=_clean(difficulty) or base_plan.difficulty,
            members=tuple(
                merged[key]
                for key in [member.seat_id.casefold() for member in base_plan.members]
                if key in merged
            ),
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
