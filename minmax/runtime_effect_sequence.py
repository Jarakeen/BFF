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
from .character_build.effect_relationship import ConditionContext
from .runtime_effect_activation import (
    RuntimeEffectActivationResult,
    apply_effect_variant_runtime_activation,
)
from .runtime_effect_eligibility import RuntimeCooldownScope, RuntimeEffectState
from .runtime_event import RuntimeEvent


def effect_variant_runtime_binding_key(
    effect: EffectVariant,
) -> tuple[str, str, str, str]:
    """Stable provenance key for binding one runtime attempt to one effect source."""

    return (
        str(effect.name or "").strip().casefold(),
        str(effect.source or "").strip().casefold(),
        str(getattr(effect.active_bar, "value", effect.active_bar) or "")
        .strip()
        .casefold(),
        str(getattr(effect, "source_slot", "") or "").strip().casefold(),
    )


@dataclass(frozen=True)
class RuntimeEffectEventAttempt:
    """One observed runtime event plus deterministic chance/condition evidence.

    bound_effect_key is optional. When present, the attempt belongs only to
    the exact EffectVariant source identified by name/source/bar/source-slot.
    Unbound attempts preserve historical shared-trigger behavior.
    """

    event: RuntimeEvent
    chance_roll: float | None = None
    condition_context: ConditionContext | None = None
    bound_effect_key: tuple[str, str, str, str] | None = None

    def __post_init__(self) -> None:
        if self.bound_effect_key is None:
            return
        key = tuple(
            str(value or "").strip().casefold()
            for value in self.bound_effect_key
        )
        if len(key) != 4 or not key[0] or not key[1]:
            raise ValueError(
                "runtime attempt bound_effect_key requires name/source/bar/source-slot provenance"
            )
        object.__setattr__(self, "bound_effect_key", key)

    @classmethod
    def for_bound_effect(
        cls,
        *,
        event: RuntimeEvent,
        effect: EffectVariant,
        chance_roll: float | None = None,
        condition_context: ConditionContext | None = None,
    ) -> "RuntimeEffectEventAttempt":
        return cls(
            event=event,
            chance_roll=chance_roll,
            condition_context=condition_context,
            bound_effect_key=effect_variant_runtime_binding_key(effect),
        )

    def applies_to(self, effect: EffectVariant) -> bool:
        return (
            self.bound_effect_key is None
            or self.bound_effect_key == effect_variant_runtime_binding_key(effect)
        )


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
        if not attempt.applies_to(effect):
            continue
        activation = apply_effect_variant_runtime_activation(
            attempt.event,
            effect,
            state=state,
            cooldown_scope=cooldown_scope,
            chance_roll=attempt.chance_roll,
            condition_context=attempt.condition_context,
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
