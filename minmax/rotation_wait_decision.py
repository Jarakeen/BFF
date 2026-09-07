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

    ``next_decision_time_seconds`` is retained as diagnostic evidence for the next
    scheduled non-light-attack decision. ``next_hard_boundary_time_seconds`` is the
    next timeline action that a multi-slot channel may not displace, such as a bar
    swap or an action on another bar. Ordinary same-bar skills are soft decisions
    that a verified channel reservation may consume and displace forward.
    """

    time_seconds: float
    bar: str | None
    candidate: RotationAction
    slot: RotationAction
    next_due: tuple[tuple[str, str | None, float], ...]
    rules: tuple[RotationRecastRule, ...]
    next_decision_time_seconds: float | None = None
    next_hard_boundary_time_seconds: float | None = None
    plan_end_seconds: float | None = None


@dataclass(frozen=True)
class PrematureRecastDecision:
    """One proven replacement plus optional timeline reservation.

    ``reservation_seconds`` is zero for ordinary instantaneous/GCD replacements.
    A positive value means the replacement occupies the modeled timeline until
    ``time_seconds + reservation_seconds`` and same-bar skill decisions strictly
    inside that interval must be displaced rather than executed concurrently.
    """

    action: RotationAction
    reservation_seconds: float = 0.0

    def __post_init__(self) -> None:
        reservation = float(self.reservation_seconds)
        if reservation < 0:
            raise ValueError("premature-recast decision reservation cannot be negative")
        object.__setattr__(self, "reservation_seconds", reservation)


PrematureRecastDecisionProvider = Callable[
    [PrematureRecastDecisionContext],
    RotationAction | PrematureRecastDecision | None,
]
