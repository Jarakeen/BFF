from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .rotation_plan import RotationAction
from .rotation_recast import RotationRecastRule


@dataclass(frozen=True)
class PrematureRecastDecisionContext:
    """Evidence exposed when duration refinement would otherwise schedule WAIT.

    The duration scheduler owns only timing evidence. It does not decide whether
    a heavy attack, proc-maintenance action, emergency heal, or other action is
    legal. A caller-supplied decision provider may use this context together with
    its own priority, sustain, build-effect, and encounter evidence and return one
    already-proven replacement action.

    ``next_decision_time_seconds`` is the next scheduled non-light-attack decision
    after this slot, when one exists. ``plan_end_seconds`` is the fixed plan horizon.
    These values let channel-based decisions prove that an action fits before the
    next scheduled decision instead of overlapping future actions silently.
    """

    time_seconds: float
    bar: str | None
    candidate: RotationAction
    slot: RotationAction
    next_due: tuple[tuple[str, str | None, float], ...]
    rules: tuple[RotationRecastRule, ...]
    next_decision_time_seconds: float | None = None
    plan_end_seconds: float | None = None


PrematureRecastDecisionProvider = Callable[
    [PrematureRecastDecisionContext],
    RotationAction | None,
]
