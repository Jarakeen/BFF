from __future__ import annotations

"""Deterministic ordered Phase 7 runtime processing for one EffectVariant.

This is the orchestration layer above the already-canonical event-attempt,
eligibility, activation, active-window, and stacking transitions. It carries the
complete immutable RuntimeEffectRuntimeState through an ordered stream without
reimplementing any lower-level combat semantics.
"""

from dataclasses import dataclass
from typing import Iterable

from .character_build.effect_instance import EffectVariant
from .runtime_effect_eligibility import RuntimeCooldownScope
from .runtime_effect_runtime import (
    RuntimeEffectRuntimeState,
    RuntimeEffectTransitionResult,
    apply_effect_variant_runtime_event,
)
from .runtime_effect_sequence import (
    RuntimeEffectEventAttempt,
    order_runtime_effect_attempts,
)


@dataclass(frozen=True)
class RuntimeEffectStreamStep:
    """One ordered event attempt and its complete effect-state transition."""

    attempt: RuntimeEffectEventAttempt
    transition: RuntimeEffectTransitionResult

    @property
    def activated(self) -> bool:
        return self.transition.activated

    @property
    def resolved(self) -> bool:
        return self.transition.resolved


@dataclass(frozen=True)
class RuntimeEffectStreamResult:
    """Auditable ordered transitions plus the complete final runtime state."""

    steps: tuple[RuntimeEffectStreamStep, ...]
    final_state: RuntimeEffectRuntimeState

    @property
    def activation_count(self) -> int:
        return sum(1 for step in self.steps if step.activated)

    @property
    def unresolved_steps(self) -> tuple[RuntimeEffectStreamStep, ...]:
        return tuple(step for step in self.steps if not step.resolved)

    @property
    def resolved(self) -> bool:
        return not self.unresolved_steps


def process_effect_variant_runtime_stream(
    attempts: Iterable[RuntimeEffectEventAttempt],
    effect: EffectVariant,
    *,
    initial_state: RuntimeEffectRuntimeState = RuntimeEffectRuntimeState(),
    cooldown_scope: RuntimeCooldownScope = RuntimeCooldownScope.GLOBAL,
) -> RuntimeEffectStreamResult:
    """Process a complete ordered runtime stream for one canonical effect.

    Each attempt keeps its deterministic chance roll attached while ordering by
    RuntimeEvent time/sequence. The complete state returned from one transition
    becomes the input to the next transition, so cooldown history, active
    windows, refreshes, and stacks advance together.

    An unresolved transition is retained in the audit trail but does not abort
    later event processing. This is intentional: missing runtime semantics remain
    explicit while independently resolvable later events continue to be modeled.
    """

    state = initial_state
    steps: list[RuntimeEffectStreamStep] = []

    for attempt in order_runtime_effect_attempts(attempts):
        transition = apply_effect_variant_runtime_event(
            attempt.event,
            effect,
            state=state,
            cooldown_scope=cooldown_scope,
            chance_roll=attempt.chance_roll,
        )
        state = transition.state
        steps.append(
            RuntimeEffectStreamStep(
                attempt=attempt,
                transition=transition,
            )
        )

    return RuntimeEffectStreamResult(
        steps=tuple(steps),
        final_state=state,
    )
