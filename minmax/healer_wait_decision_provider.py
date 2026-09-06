from __future__ import annotations

from dataclasses import dataclass

from .heavy_attack_opportunity import (
    HeavyAttackOpportunityEvidence,
    HeavyAttackPurpose,
    evaluate_heavy_attack_opportunity,
)
from .rotation_plan import RotationAction, RotationActionKind
from .rotation_wait_decision import PrematureRecastDecisionContext


@dataclass(frozen=True)
class HealerHeavyAttackCandidate:
    """One caller-proven heavy-attack opportunity for an exact saved bar.

    The provider deliberately does not infer set, passive, sustain, or encounter
    facts. Those layers supply ``HeavyAttackOpportunityEvidence`` for the current
    decision point. This adapter only chooses among proven candidates and converts
    the winning opportunity into a concrete same-bar HEAVY_ATTACK action.
    """

    bar: str
    evidence: HeavyAttackOpportunityEvidence

    def __post_init__(self) -> None:
        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("healer heavy attack candidate bar must be front or back")
        object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class HealerWaitDecisionProvider:
    """Use explicit healer heavy evidence before accepting a duration WAIT.

    REQUIRED_EFFECT candidates outrank RECOVERY candidates. Within the same
    purpose, caller order is preserved deliberately; this layer has no authority
    to invent relative value between two independently proven effects.
    Candidates on the inactive bar are ignored because bar-swap policy belongs to
    the rotation decision pipeline rather than duration refinement.
    """

    candidates: tuple[HealerHeavyAttackCandidate, ...]

    def __call__(self, context: PrematureRecastDecisionContext) -> RotationAction | None:
        bar = str(context.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            return None

        ordered = sorted(
            enumerate(self.candidates),
            key=lambda item: (
                0
                if item[1].evidence.purpose is HeavyAttackPurpose.REQUIRED_EFFECT
                else 1,
                item[0],
            ),
        )
        for _, candidate in ordered:
            if candidate.bar != bar:
                continue
            opportunity = evaluate_heavy_attack_opportunity(candidate.evidence)
            if not opportunity.recommended:
                continue
            return RotationAction(
                time_seconds=context.time_seconds,
                sequence=context.slot.sequence,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="Heavy Attack",
                bar=bar,
            )
        return None
