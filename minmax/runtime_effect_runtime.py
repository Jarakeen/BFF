from __future__ import annotations

"""One deterministic Phase 7 transition for a canonical EffectVariant.

Lower-level modules remain authoritative for eligibility, cooldown history,
active-window creation, and stacking semantics. This module only composes those
steps into one auditable runtime result for callers that need current effect
state after processing an event.
"""

from dataclasses import dataclass

from .character_build.effect_instance import EffectVariant
from .runtime_effect_activation import (
    RuntimeEffectActivationResult,
    apply_effect_variant_runtime_activation,
)
from .runtime_effect_eligibility import RuntimeCooldownScope, RuntimeEffectState
from .runtime_effect_stacking import (
    RuntimeEffectStackingResult,
    apply_runtime_effect_window_stacking,
)
from .runtime_effect_window import (
    RuntimeEffectActiveWindow,
    active_window_from_effect_activation,
)
from .runtime_event import RuntimeEvent


@dataclass(frozen=True)
class RuntimeEffectRuntimeState:
    """Immutable runtime state for one canonical EffectVariant instance."""

    activation_state: RuntimeEffectState = RuntimeEffectState()
    windows: tuple[RuntimeEffectActiveWindow, ...] = ()


@dataclass(frozen=True)
class RuntimeEffectTransitionResult:
    """One event attempt plus the resulting runtime state."""

    event: RuntimeEvent
    activation: RuntimeEffectActivationResult
    state: RuntimeEffectRuntimeState
    stacking: RuntimeEffectStackingResult | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def activated(self) -> bool:
        return self.activation.activated

    @property
    def resolved(self) -> bool:
        return not self.unresolved


def apply_effect_variant_runtime_event(
    event: RuntimeEvent,
    effect: EffectVariant,
    *,
    state: RuntimeEffectRuntimeState = RuntimeEffectRuntimeState(),
    cooldown_scope: RuntimeCooldownScope = RuntimeCooldownScope.GLOBAL,
    chance_roll: float | None = None,
) -> RuntimeEffectTransitionResult:
    """Apply one event to activation history and bounded active-window state.

    Failed activation preserves both cooldown and window history. Successful
    instantaneous/unbounded effects update activation history but create no
    bounded window. Successful bounded effects use ``EffectVariant.stacking``;
    if stacking semantics are absent, the activation remains recorded while the
    window transition is reported unresolved instead of guessed.
    """

    activation = apply_effect_variant_runtime_activation(
        event,
        effect,
        state=state.activation_state,
        cooldown_scope=cooldown_scope,
        chance_roll=chance_roll,
    )

    if not activation.activated:
        return RuntimeEffectTransitionResult(
            event=event,
            activation=activation,
            state=state,
        )

    new_window = active_window_from_effect_activation(event, effect, activation)
    if new_window is None:
        return RuntimeEffectTransitionResult(
            event=event,
            activation=activation,
            state=RuntimeEffectRuntimeState(
                activation_state=activation.state,
                windows=state.windows,
            ),
        )

    stacking = apply_runtime_effect_window_stacking(
        state.windows,
        new_window,
        behavior=effect.stacking,
    )
    if not stacking.resolved:
        return RuntimeEffectTransitionResult(
            event=event,
            activation=activation,
            state=RuntimeEffectRuntimeState(
                activation_state=activation.state,
                windows=state.windows,
            ),
            stacking=stacking,
            unresolved=stacking.unresolved,
        )

    return RuntimeEffectTransitionResult(
        event=event,
        activation=activation,
        state=RuntimeEffectRuntimeState(
            activation_state=activation.state,
            windows=stacking.retained,
        ),
        stacking=stacking,
    )
