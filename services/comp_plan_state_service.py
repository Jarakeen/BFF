from __future__ import annotations

"""Lossless RaidPlan <-> CompPlanState boundary for the Comp Maker rebuild."""

from dataclasses import replace

from models.comp_plan_state import CompChairState, CompPlanState
from models.raid_plan import RaidPlan, RaidPlanMember


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


class CompPlanStateService:
    """Translate Raid Plan decisions into one canonical Comp Maker working state."""

    @staticmethod
    def from_raid_plan(
        plan: RaidPlan,
        *,
        achievement_goal: str | None = None,
    ) -> CompPlanState:
        if not isinstance(plan, RaidPlan):
            raise TypeError("Comp state requires a RaidPlan")

        chairs = tuple(
            CompChairState(
                seat_id=member.seat_id,
                player_name=member.gamertag,
                roster_member_id=member.roster_member_id,
                player_id=member.player_id,
                character_id=member.character_id,
                character_name=member.character_name,
                role=member.role,
                eso_class=member.eso_class,
                selected_build_id=member.selected_build_id,
                selected_build_name=member.selected_build_name,
                build_source_kind=member.build_source_kind,
                build_source_name=member.build_source_name,
                build_source_url=member.build_source_url,
                candidate_id=member.candidate_id,
                planned_gear_sets=member.planned_gear_sets,
                planned_skills=member.planned_skills,
                planned_mundus=member.planned_mundus,
                primary_assignment=member.primary_assignment,
                secondary_assignment=member.secondary_assignment,
                utility_assignments=member.utility_assignments,
                locked_fields=member.comp_locked_fields,
                notes=member.notes,
            )
            for member in plan.members
        )
        return CompPlanState(
            raid_plan_id=plan.plan_id,
            raid_plan_name=plan.name,
            trial_id=plan.trial_id,
            team_name=plan.team_name,
            difficulty=plan.difficulty,
            status=plan.status,
            plan_note=plan.plan_note,
            achievement_goal=achievement_goal,
            chairs=chairs,
            dirty=False,
        )

    @staticmethod
    def to_raid_plan(
        state: CompPlanState,
        *,
        base_plan: RaidPlan,
    ) -> RaidPlan:
        """Apply Comp-owned chair state without dropping unrelated Raid Plan state."""
        if not isinstance(state, CompPlanState):
            raise TypeError("state must be CompPlanState")
        if not isinstance(base_plan, RaidPlan):
            raise TypeError("base_plan must be RaidPlan")
        if state.raid_plan_id.casefold() != base_plan.plan_id.casefold():
            raise ValueError("Comp state does not belong to the supplied Raid Plan")

        existing_by_seat = {
            member.seat_id.casefold(): member
            for member in base_plan.members
        }
        state_by_seat = {
            chair.seat_id.casefold(): chair
            for chair in state.chairs
        }

        members: list[RaidPlanMember] = []
        ordered_keys = [member.seat_id.casefold() for member in base_plan.members]
        ordered_keys.extend(
            key for key in state_by_seat if key not in existing_by_seat
        )

        for key in ordered_keys:
            chair = state_by_seat.get(key)
            prior = existing_by_seat.get(key)
            if chair is None:
                if prior is not None:
                    members.append(prior)
                continue

            values = dict(
                seat_id=chair.seat_id,
                gamertag=chair.player_name,
                roster_member_id=chair.roster_member_id,
                player_id=chair.player_id,
                character_id=chair.character_id,
                character_name=chair.character_name,
                role=chair.role,
                eso_class=chair.eso_class,
                selected_build_id=chair.selected_build_id,
                selected_build_name=chair.selected_build_name,
                build_source_kind=chair.build_source_kind,
                build_source_name=chair.build_source_name,
                build_source_url=chair.build_source_url,
                candidate_id=chair.candidate_id,
                planned_gear_sets=chair.planned_gear_sets,
                planned_skills=chair.planned_skills,
                planned_mundus=chair.planned_mundus,
                primary_assignment=chair.primary_assignment,
                secondary_assignment=chair.secondary_assignment,
                utility_assignments=chair.utility_assignments,
                comp_locked_fields=chair.locked_fields,
                notes=chair.notes,
            )
            members.append(
                prior.with_selection(**values)
                if prior is not None
                else RaidPlanMember(**values)
            )

        return replace(
            base_plan,
            name=state.raid_plan_name,
            trial_id=state.trial_id,
            team_name=state.team_name,
            difficulty=state.difficulty,
            status=state.status,
            plan_note=state.plan_note,
            members=tuple(members),
        )

    @staticmethod
    def lock(
        state: CompPlanState,
        *,
        seat_id: str,
        field_name: str,
        locked: bool = True,
    ) -> CompPlanState:
        chair = state.chair(seat_id)
        if chair is None:
            raise ValueError(f"unknown Comp chair: {seat_id!r}")
        wanted = _clean(field_name).casefold()
        locks = list(chair.locked_fields)
        present = wanted in locks
        if locked and not present:
            locks.append(wanted)
        elif not locked and present:
            locks.remove(wanted)
        revised = chair.with_changes(locked_fields=tuple(locks))
        return state.with_chair(revised)


__all__ = ["CompPlanStateService"]
