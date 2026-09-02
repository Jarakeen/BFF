from __future__ import annotations

"""Deterministic ordered event processing for one canonical EffectVariant.

Each attempt keeps its own caller-supplied chance roll attached to the observed
RuntimeEvent before ordering. RuntimeEffectState is then carried forward through
successful activations, so cooldown history is part of the sequence rather than
recomputed from isolated events.
"""

from dataclasses import dataclass
from typing import Iterable

from .character_build.effect_instance import EffectVariant
from .runtime_effect_activation import (
    RuntimeEffectActivationResult,
    apply_effect_variant_runtime_activation,
)
from .runtime_effect_eligibility import RuntimeCooldownScope, RuntimeEffectState
from .runtime_event import RuntimeEvent


@dataclass(frozen=True)
class RuntimeEffectEventAttempt:
    """One observed runtime event and its deterministic chance input, if any."""

    event: RuntimeEvent
    chance_roll: float | None = None


@dataclass(frozen=True)
class RuntimeEffectSequenceStep:
    """Auditable result for one ordered event attempt."""

    attempt: RuntimeEffectEventAttempt
    activation: RuntimeEffectActivationResult


@dataclass(frozen=True)
class RuntimeEffectSequenceResult:
    """Ordered activation decisions and the state remaining after the sequence."""

    steps: tuple[RuntimeEffectSequenceStep, ...]
    final_state: RuntimeEffectState

    @property
    def activation_count(self) -> int:
        return sum(1 for step in self.steps if step.activation.activated)


def order_runtime_effect_attempts(
    attempts: Iterable[RuntimeEffectEventAttempt],
) -> tuple[RuntimeEffectEventAttempt, ...]:
    """Order attempts by the same timestamp/sequence contract as RuntimeEvent."""

    return tuple(
        sorted(
            attempts,
            key=lambda attempt: (
                attempt.event.time_seconds,
                attempt.event.sequence,
            ),
        )
    )


def process_effect_variant_runtime_sequence(
    attempts: Iterable[RuntimeEffectEventAttempt],
    effect: EffectVariant,
    *,
    initial_state: RuntimeEffectState = RuntimeEffectState(),
    cooldown_scope: RuntimeCooldownScope = RuntimeCooldownScope.GLOBAL,
) -> RuntimeEffectSequenceResult:
    """Process ordered runtime attempts while carrying immutable effect state.

    This function owns no trigger, chance, or cooldown semantics itself. Each
    ordered attempt is delegated to the existing activation transition, and the
    returned state becomes the input state for the next attempt. Failed attempts
    therefore preserve prior history exactly.
    """

    state = initial_state
    steps: list[RuntimeEffectSequenceStep] = []

    for attempt in order_runtime_effect_attempts(attempts):
        activation = apply_effect_variant_runtime_activation(
            attempt.event,
            effect,
            state=state,
            cooldown_scope=cooldown_scope,
            chance_roll=attempt.chance_roll,
        )
        state = activation.state
        steps.append(
            RuntimeEffectSequenceStep(
                attempt=attempt,
                activation=activation,
            )
        )

    return RuntimeEffectSequenceResult(
        steps=tuple(steps),
        final_state=state,
    )
