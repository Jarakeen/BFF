from __future__ import annotations

from dataclasses import dataclass
import math

from .healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)


@dataclass(frozen=True)
class HeavyAttackEffectRuntimeState:
    """Observed runtime state for one heavy-triggered build effect.

    ``last_trigger_seconds`` is the timestamp of the last qualifying fully charged
    heavy attack that actually triggered the effect. ``None`` means no qualifying
    trigger has occurred during the modeled timeline.
    """

    incentive_name: str
    bar: str
    last_trigger_seconds: float | None = None

    def __post_init__(self) -> None:
        name = str(self.incentive_name or "").strip()
        if not name:
            raise ValueError("heavy attack runtime incentive name is required")
        object.__setattr__(self, "incentive_name", name)

        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("heavy attack runtime bar must be front or back")
        object.__setattr__(self, "bar", bar)

        if self.last_trigger_seconds is not None:
            value = float(self.last_trigger_seconds)
            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    "heavy attack runtime last trigger must be finite and non-negative"
                )
            object.__setattr__(self, "last_trigger_seconds", value)


@dataclass(frozen=True)
class RequiredHeavyAttackDueState:
    """Derived due-state for one required heavy-attack build incentive."""

    incentive: HealerHeavyAttackBuildIncentive
    current_time_seconds: float
    due: bool
    next_eligible_seconds: float
    effect_expires_seconds: float | None
    seconds_until_due: float
    reason: str


def evaluate_required_heavy_attack_due_state(
    *,
    incentive: HealerHeavyAttackBuildIncentive,
    current_time_seconds: float,
    runtime: HeavyAttackEffectRuntimeState | None = None,
) -> RequiredHeavyAttackDueState:
    """Evaluate when a required-effect heavy may/should be triggered again.

    The recurrence comes only from verified static incentive evidence. This
    function does not decide encounter safety, channel duration, ability priority,
    resource state, or whether a candidate heavy actually lands. Those remain
    caller-owned runtime facts.

    Effect expiry is diagnostic and uses the build-effective duration when the
    shared duration layer has resolved one. The source mechanic's base/capped
    duration remains preserved separately on the incentive.
    """

    if incentive.kind is not HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT:
        raise ValueError("heavy attack due-state requires a required-effect incentive")
    if incentive.recurrence_seconds is None:
        raise ValueError("required heavy attack incentive has no verified recurrence")

    recurrence = float(incentive.recurrence_seconds)
    now = float(current_time_seconds)
    if not math.isfinite(recurrence) or recurrence <= 0:
        raise ValueError("required heavy attack recurrence must be finite and positive")
    if not math.isfinite(now) or now < 0:
        raise ValueError("heavy attack due-state time must be finite and non-negative")

    last_trigger: float | None = None
    if runtime is not None:
        if runtime.incentive_name.casefold() != incentive.name.casefold():
            raise ValueError(
                "heavy attack runtime incentive does not match static incentive: "
                f"{runtime.incentive_name!r} != {incentive.name!r}"
            )
        if runtime.bar != incentive.bar:
            raise ValueError(
                "heavy attack runtime bar does not match static incentive: "
                f"{runtime.bar!r} != {incentive.bar!r}"
            )
        last_trigger = runtime.last_trigger_seconds

    if last_trigger is None:
        return RequiredHeavyAttackDueState(
            incentive=incentive,
            current_time_seconds=now,
            due=True,
            next_eligible_seconds=now,
            effect_expires_seconds=None,
            seconds_until_due=0.0,
            reason=f"{incentive.name} has no qualifying heavy trigger in the modeled timeline",
        )

    next_eligible = last_trigger + recurrence
    effect_expires: float | None = None
    duration_value = (
        incentive.effective_effect_duration_seconds
        if incentive.effective_effect_duration_seconds is not None
        else incentive.maximum_effect_duration_seconds
    )
    if duration_value is not None:
        duration = float(duration_value)
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("heavy attack effect duration must be finite and non-negative")
        effect_expires = last_trigger + duration

    due = now >= next_eligible
    seconds_until_due = max(0.0, next_eligible - now)
    reason = (
        f"{incentive.name} required heavy is eligible now"
        if due
        else f"{incentive.name} required heavy becomes eligible in {seconds_until_due:g}s"
    )
    return RequiredHeavyAttackDueState(
        incentive=incentive,
        current_time_seconds=now,
        due=due,
        next_eligible_seconds=next_eligible,
        effect_expires_seconds=effect_expires,
        seconds_until_due=seconds_until_due,
        reason=reason,
    )
