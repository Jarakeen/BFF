from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .rotation_plan import RotationAction, RotationPlan
from .rotation_reserve_adjustment import (
    RotationReserveAdjustmentProposal,
    WithheldRotationAction,
)


class PostDemandDisposition(str, Enum):
    """Explicit policy outcome for one reserve-withheld rotation action."""

    RESCHEDULE = "reschedule"
    OMIT = "omit"


@dataclass(frozen=True)
class PostDemandActionDirective:
    """Caller-supplied disposition for one exact withheld action.

    Rescheduling time and sequence are policy inputs. This layer only validates
    that a requested replacement is after the demand window, remains inside the
    plan, and does not collide with another scheduled action.
    """

    original_time_seconds: float
    original_sequence: int
    disposition: PostDemandDisposition
    new_time_seconds: float | None = None
    new_sequence: int | None = None

    def __post_init__(self) -> None:
        original_time = float(self.original_time_seconds)
        if not math.isfinite(original_time) or original_time < 0:
            raise ValueError("post-demand original action time must be finite and non-negative")
        object.__setattr__(self, "original_time_seconds", original_time)

        original_sequence = int(self.original_sequence)
        if original_sequence < 0:
            raise ValueError("post-demand original action sequence cannot be negative")
        object.__setattr__(self, "original_sequence", original_sequence)

        if not isinstance(self.disposition, PostDemandDisposition):
            object.__setattr__(
                self,
                "disposition",
                PostDemandDisposition(str(self.disposition)),
            )

        if self.disposition is PostDemandDisposition.OMIT:
            if self.new_time_seconds is not None or self.new_sequence is not None:
                raise ValueError("omitted post-demand action cannot define replacement timing")
            return

        if self.new_time_seconds is None or self.new_sequence is None:
            raise ValueError("rescheduled post-demand action requires new time and sequence")

        new_time = float(self.new_time_seconds)
        if not math.isfinite(new_time) or new_time < 0:
            raise ValueError("post-demand replacement time must be finite and non-negative")
        object.__setattr__(self, "new_time_seconds", new_time)

        new_sequence = int(self.new_sequence)
        if new_sequence < 0:
            raise ValueError("post-demand replacement sequence cannot be negative")
        object.__setattr__(self, "new_sequence", new_sequence)


@dataclass(frozen=True)
class PostDemandActionOutcome:
    withheld: WithheldRotationAction
    disposition: PostDemandDisposition
    replacement_action: RotationAction | None = None


@dataclass(frozen=True)
class RotationPostDemandRescheduleProposal:
    reserve_adjustment: RotationReserveAdjustmentProposal
    adjusted_plan: RotationPlan
    outcomes: tuple[PostDemandActionOutcome, ...]


def propose_post_demand_reschedule(
    *,
    reserve_adjustment: RotationReserveAdjustmentProposal,
    directives: tuple[PostDemandActionDirective, ...],
) -> RotationPostDemandRescheduleProposal:
    """Apply explicit post-demand policy to every reserve-withheld action.

    The function never chooses a replacement time or silently drops an action.
    Every withheld action requires exactly one directive. ``RESCHEDULE`` must be
    placed at or after the end of the triggering demand window and within the
    original plan duration. Existing and replacement action-order collisions are
    rejected rather than repaired heuristically.
    """

    demand = reserve_adjustment.protection_plan.analysis.demand
    plan = reserve_adjustment.adjusted_plan

    withheld_by_key = {
        (float(item.action.time_seconds), item.action.sequence): item
        for item in reserve_adjustment.withheld_actions
    }
    directive_by_key: dict[tuple[float, int], PostDemandActionDirective] = {}

    for directive in directives:
        key = (directive.original_time_seconds, directive.original_sequence)
        if key in directive_by_key:
            raise ValueError(
                "duplicate post-demand directive for action: "
                f"{directive.original_time_seconds:g}s sequence {directive.original_sequence}"
            )
        if key not in withheld_by_key:
            raise ValueError(
                "post-demand directive does not match a withheld action: "
                f"{directive.original_time_seconds:g}s sequence {directive.original_sequence}"
            )
        directive_by_key[key] = directive

    missing = set(withheld_by_key) - set(directive_by_key)
    if missing:
        time_seconds, sequence = sorted(missing)[0]
        raise ValueError(
            "withheld action is missing explicit post-demand disposition: "
            f"{time_seconds:g}s sequence {sequence}"
        )

    occupied = {
        (float(action.time_seconds), action.sequence)
        for action in plan.actions
    }
    replacements: list[RotationAction] = []
    outcomes: list[PostDemandActionOutcome] = []

    for key in sorted(withheld_by_key):
        withheld = withheld_by_key[key]
        directive = directive_by_key[key]

        if directive.disposition is PostDemandDisposition.OMIT:
            outcomes.append(
                PostDemandActionOutcome(
                    withheld=withheld,
                    disposition=directive.disposition,
                )
            )
            continue

        assert directive.new_time_seconds is not None
        assert directive.new_sequence is not None
        if directive.new_time_seconds < demand.end_seconds:
            raise ValueError(
                "post-demand replacement must occur at or after demand end: "
                f"{directive.new_time_seconds:g}s < {demand.end_seconds:g}s"
            )
        if directive.new_time_seconds > plan.duration_seconds:
            raise ValueError("post-demand replacement cannot occur after plan duration")

        replacement_key = (directive.new_time_seconds, directive.new_sequence)
        if replacement_key in occupied:
            raise ValueError(
                "post-demand replacement collides with another rotation action: "
                f"{directive.new_time_seconds:g}s sequence {directive.new_sequence}"
            )
        occupied.add(replacement_key)

        original = withheld.action
        replacement = RotationAction(
            time_seconds=directive.new_time_seconds,
            sequence=directive.new_sequence,
            kind=original.kind,
            name=original.name,
            bar=original.bar,
        )
        replacements.append(replacement)
        outcomes.append(
            PostDemandActionOutcome(
                withheld=withheld,
                disposition=directive.disposition,
                replacement_action=replacement,
            )
        )

    adjusted = RotationPlan(
        character_name=plan.character_name,
        build_name=plan.build_name,
        duration_seconds=plan.duration_seconds,
        actions=plan.actions + tuple(replacements),
        assumptions=plan.assumptions + (
            "post-demand replacements use explicit caller-supplied timing and disposition; no role policy is inferred",
        ),
        unresolved=plan.unresolved,
    )

    return RotationPostDemandRescheduleProposal(
        reserve_adjustment=reserve_adjustment,
        adjusted_plan=adjusted,
        outcomes=tuple(outcomes),
    )
