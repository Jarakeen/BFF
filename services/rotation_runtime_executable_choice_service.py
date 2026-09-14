from __future__ import annotations

"""Choose an immediately executable runtime strategy without materializing an action.

This boundary consumes already-proven runtime execution-strategy candidates and the
existing deterministic RotationPlan. It may select exactly one candidate only when the
candidate is on the currently active bar and explicit slot, target-state, and occupancy
evidence prove that inserting the skill at the activation instant is legal.

A candidate on the inactive bar is not auto-routed through a BAR_SWAP. Missing legality
evidence remains unresolved. Even a selected choice is still not a RotationAction; the
later materialization boundary owns sequence insertion and plan mutation.
"""

from dataclasses import dataclass

from minmax.rotation_action_occupancy import (
    RotationActionOccupancyAssessor,
    RotationActionOccupancyRequirement,
)
from minmax.rotation_action_slot_legality import (
    RotationActionSlotAssessor,
    RotationActionSlotRequirement,
)
from minmax.rotation_action_target_legality import (
    RotationActionTargetAssessor,
    RotationActionTargetRequirement,
    RotationTargetStateWindow,
)
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_runtime_execution_strategy_service import (
    RotationRuntimeExecutionStrategyCandidate,
    RotationRuntimeExecutionStrategyResolution,
)


def _matching_occupancy_requirement(
    candidate: RotationRuntimeExecutionStrategyCandidate,
    requirements: tuple[RotationActionOccupancyRequirement, ...],
) -> RotationActionOccupancyRequirement | None:
    matches = tuple(
        row
        for row in requirements
        if row.action_kind is RotationActionKind.SKILL
        and row.action_name.casefold() == candidate.skill_name.casefold()
        and (row.bar is None or row.bar == candidate.bar)
    )
    if len(matches) > 1:
        raise ValueError(
            f"multiple occupancy requirements match runtime strategy {candidate.skill_name!r}"
        )
    return matches[0] if matches else None


def _matching_target_requirement(
    candidate: RotationRuntimeExecutionStrategyCandidate,
    requirements: tuple[RotationActionTargetRequirement, ...],
) -> RotationActionTargetRequirement | None:
    matches = tuple(
        row
        for row in requirements
        if row.action_kind is RotationActionKind.SKILL
        and row.action_name is not None
        and row.action_name.casefold() == candidate.skill_name.casefold()
        and (row.bar is None or row.bar == candidate.bar)
    )
    if len(matches) > 1:
        raise ValueError(
            f"multiple target requirements match runtime strategy {candidate.skill_name!r}"
        )
    return matches[0] if matches else None


@dataclass(frozen=True)
class RotationRuntimeExecutableChoice:
    """One strategy proven immediately executable at its activation instant."""

    candidate: RotationRuntimeExecutionStrategyCandidate
    active_bar: str

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, RotationRuntimeExecutionStrategyCandidate):
            raise TypeError("runtime executable choice requires a strategy candidate")
        bar = str(self.active_bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("runtime executable choice active_bar must be front or back")
        if self.candidate.bar != bar:
            raise ValueError("runtime executable choice candidate is not on the active bar")
        object.__setattr__(self, "active_bar", bar)


@dataclass(frozen=True)
class RotationRuntimeExecutableChoiceResolution:
    selected: RotationRuntimeExecutableChoice | None = None
    executable_candidates: tuple[RotationRuntimeExecutionStrategyCandidate, ...] = ()
    requires_bar_swap: tuple[RotationRuntimeExecutionStrategyCandidate, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.selected is not None and not self.unresolved


class RotationRuntimeExecutableChoiceService:
    """Select one proven immediately executable runtime strategy candidate."""

    def __init__(
        self,
        *,
        active_bar_assessor: RotationActiveBarAssessor | None = None,
        slot_assessor: RotationActionSlotAssessor | None = None,
        target_assessor: RotationActionTargetAssessor | None = None,
        occupancy_assessor: RotationActionOccupancyAssessor | None = None,
    ) -> None:
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()
        self.slot_assessor = slot_assessor or RotationActionSlotAssessor()
        self.target_assessor = target_assessor or RotationActionTargetAssessor()
        self.occupancy_assessor = occupancy_assessor or RotationActionOccupancyAssessor()

    def resolve(
        self,
        *,
        plan: RotationPlan,
        strategy: RotationRuntimeExecutionStrategyResolution,
        slot_requirements: tuple[RotationActionSlotRequirement, ...],
        target_requirements: tuple[RotationActionTargetRequirement, ...],
        target_windows: tuple[RotationTargetStateWindow, ...],
        occupancy_requirements: tuple[RotationActionOccupancyRequirement, ...],
        initial_bar: str = "front",
    ) -> RotationRuntimeExecutableChoiceResolution:
        if not isinstance(plan, RotationPlan):
            raise TypeError("runtime executable choice requires RotationPlan")
        if not isinstance(strategy, RotationRuntimeExecutionStrategyResolution):
            raise TypeError(
                "runtime executable choice requires RotationRuntimeExecutionStrategyResolution"
            )
        if strategy.unresolved:
            return RotationRuntimeExecutableChoiceResolution(
                unresolved=tuple(strategy.unresolved),
            )
        if not strategy.candidates:
            return RotationRuntimeExecutableChoiceResolution(
                unresolved=("runtime execution strategy has no candidates",),
            )

        activation_time = float(strategy.activated_intent.activated_at_seconds)
        if activation_time > plan.duration_seconds:
            return RotationRuntimeExecutableChoiceResolution(
                unresolved=("runtime intent activates after the deterministic plan duration",),
            )

        active_bar = self.active_bar_assessor.active_bar_at(
            plan,
            time_seconds=activation_time,
            initial_bar=initial_bar,
        )
        same_bar: list[RotationRuntimeExecutionStrategyCandidate] = []
        swap_required: list[RotationRuntimeExecutionStrategyCandidate] = []
        unresolved: list[str] = []

        for candidate in strategy.candidates:
            if candidate.bar != active_bar:
                swap_required.append(candidate)
                continue
            reasons = self._candidate_unresolved(
                plan=plan,
                candidate=candidate,
                slot_requirements=tuple(slot_requirements),
                target_requirements=tuple(target_requirements),
                target_windows=tuple(target_windows),
                occupancy_requirements=tuple(occupancy_requirements),
            )
            if reasons:
                unresolved.extend(reasons)
                continue
            same_bar.append(candidate)

        if len(same_bar) == 1:
            selected = RotationRuntimeExecutableChoice(
                candidate=same_bar[0],
                active_bar=active_bar,
            )
            return RotationRuntimeExecutableChoiceResolution(
                selected=selected,
                executable_candidates=tuple(same_bar),
                requires_bar_swap=tuple(swap_required),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        if len(same_bar) > 1:
            names = ", ".join(
                f"{row.skill_name} ({row.bar})" for row in same_bar
            )
            unresolved.append(
                "multiple runtime strategy candidates are immediately executable; "
                f"explicit execution policy must choose among: {names}"
            )
        elif swap_required and not unresolved:
            unresolved.append(
                "no runtime strategy candidate is on the active bar; explicit bar-swap "
                "execution policy is required"
            )
        elif not unresolved:
            unresolved.append("no runtime strategy candidate is immediately executable")

        return RotationRuntimeExecutableChoiceResolution(
            executable_candidates=tuple(same_bar),
            requires_bar_swap=tuple(swap_required),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _candidate_unresolved(
        self,
        *,
        plan: RotationPlan,
        candidate: RotationRuntimeExecutionStrategyCandidate,
        slot_requirements: tuple[RotationActionSlotRequirement, ...],
        target_requirements: tuple[RotationActionTargetRequirement, ...],
        target_windows: tuple[RotationTargetStateWindow, ...],
        occupancy_requirements: tuple[RotationActionOccupancyRequirement, ...],
    ) -> tuple[str, ...]:
        activation_time = float(candidate.activated_at_seconds)
        sequence = max(
            (
                int(action.sequence)
                for action in plan.actions
                if abs(float(action.time_seconds) - activation_time) <= 1e-12
            ),
            default=-1,
        ) + 1
        hypothetical = RotationAction(
            time_seconds=activation_time,
            sequence=sequence,
            kind=RotationActionKind.SKILL,
            name=candidate.skill_name,
            bar=candidate.bar,
            target_key=candidate.target_key,
        )
        trial_plan = RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=(*plan.actions, hypothetical),
            assumptions=plan.assumptions,
            unresolved=plan.unresolved,
        )

        reasons: list[str] = []
        matching_slots = tuple(
            row
            for row in slot_requirements
            if row.action_kind is RotationActionKind.SKILL
            and row.action_name.casefold() == candidate.skill_name.casefold()
        )
        if not matching_slots:
            reasons.append(
                f"{candidate.skill_name}: explicit saved-build slot requirement is missing"
            )
        elif not self.slot_assessor.assess(trial_plan, matching_slots).legal:
            reasons.append(
                f"{candidate.skill_name}: candidate fails saved-build slot legality"
            )

        if candidate.target_key is not None:
            target_requirement = _matching_target_requirement(candidate, target_requirements)
            if target_requirement is None:
                reasons.append(
                    f"{candidate.skill_name}: explicit target-kind requirement is missing"
                )
            elif not any(window.contains(activation_time) for window in target_windows):
                reasons.append(
                    f"{candidate.skill_name}: target-state evidence is missing at activation time"
                )
            elif not self.target_assessor.assess(
                trial_plan,
                (target_requirement,),
                target_windows,
            ).legal:
                reasons.append(
                    f"{candidate.skill_name}: target state is not legal at activation time"
                )

        occupancy_requirement = _matching_occupancy_requirement(
            candidate,
            occupancy_requirements,
        )
        if occupancy_requirement is None:
            reasons.append(
                f"{candidate.skill_name}: explicit action occupancy evidence is missing"
            )
        else:
            relevant_occupancy = tuple(
                row
                for row in occupancy_requirements
                if any(
                    action.kind is row.action_kind
                    and action.name is not None
                    and action.name.casefold() == row.action_name.casefold()
                    and (row.bar is None or row.bar == action.bar)
                    for action in trial_plan.actions
                )
            )
            assessment = self.occupancy_assessor.assess(
                trial_plan,
                relevant_occupancy,
            )
            if not assessment.legal:
                if any(
                    abs(row.blocked_time_seconds - activation_time) <= 1e-9
                    or abs(row.occupying_time_seconds - activation_time) <= 1e-9
                    for row in assessment.violations
                ):
                    reasons.append(
                        f"{candidate.skill_name}: activation conflicts with action occupancy"
                    )

        return tuple(dict.fromkeys(reasons))


__all__ = [
    "RotationRuntimeExecutableChoice",
    "RotationRuntimeExecutableChoiceResolution",
    "RotationRuntimeExecutableChoiceService",
]
