from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.effect_layer import EffectLayer
from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_temporal_effect_uptime_service import (
    RotationTemporalEffectApplication,
)


@dataclass(frozen=True)
class RotationPlanTemporalLegalityViolation:
    effect_name: str
    layer: EffectLayer
    source: str
    time_seconds: float
    reason: str


@dataclass(frozen=True)
class RotationPlanTemporalLegalityAssessment:
    applications: tuple[RotationTemporalEffectApplication, ...]
    violations: tuple[RotationPlanTemporalLegalityViolation, ...]
    unresolved: tuple[str, ...]

    @property
    def is_legal(self) -> bool:
        return not self.violations and not self.unresolved


class RotationPlanTemporalLegalityService:
    """Validate claimed temporal activations against the scheduled plan timeline.

    This service proves plan-level facts only:
    - the claimed activation bar matches the bar active immediately before its time;
    - a same-timestamp bar swap is unresolved because applications have no sequence;
    - ULTIMATE activations correspond to an explicit ultimate action on that bar/time;
    - CONSUMABLE activations correspond to an explicit potion action on that time.

    PROC activations do not require a dedicated plan action, but they still require
    the claimed bar to match the reconstructed active bar. Effect identity, trigger,
    canonical cooldown, and build availability remain owned by the temporal effect
    legality service.
    """

    _EPSILON = 1e-9

    def assess(
        self,
        *,
        plan: RotationPlan,
        applications: tuple[RotationTemporalEffectApplication, ...],
        initial_bar: str,
    ) -> RotationPlanTemporalLegalityAssessment:
        initial = str(initial_bar or "").strip().casefold()
        if initial not in {"front", "back"}:
            raise ValueError("rotation plan temporal legality initial_bar must be front or back")

        unresolved: list[str] = []
        violations: list[RotationPlanTemporalLegalityViolation] = []

        for application in applications:
            same_time_swaps = tuple(
                action
                for action in plan.actions
                if action.kind is RotationActionKind.BAR_SWAP
                and abs(action.time_seconds - application.time_seconds) <= self._EPSILON
            )
            if same_time_swaps:
                unresolved.append(
                    f"cannot prove active bar for {application.effect_name!r} from "
                    f"{application.source!r} at {application.time_seconds:.3f}s because "
                    "a bar swap occurs at the same timestamp and temporal applications "
                    "do not carry an action sequence"
                )
                continue

            active_bar = self._active_bar_before(
                plan=plan,
                time_seconds=application.time_seconds,
                initial_bar=initial,
            )
            if active_bar != application.bar:
                violations.append(
                    RotationPlanTemporalLegalityViolation(
                        effect_name=application.effect_name,
                        layer=application.layer,
                        source=application.source,
                        time_seconds=application.time_seconds,
                        reason=(
                            f"activation claims {application.bar} bar, but the rotation "
                            f"plan has {active_bar} bar active"
                        ),
                    )
                )
                continue

            if application.layer is EffectLayer.ULTIMATE:
                matching = tuple(
                    action
                    for action in plan.actions
                    if action.kind is RotationActionKind.ULTIMATE
                    and abs(action.time_seconds - application.time_seconds) <= self._EPSILON
                    and action.bar == application.bar
                    and action.name is not None
                    and self._stable_name(action.name) == self._stable_name(application.source)
                )
                if len(matching) != 1:
                    violations.append(
                        RotationPlanTemporalLegalityViolation(
                            effect_name=application.effect_name,
                            layer=application.layer,
                            source=application.source,
                            time_seconds=application.time_seconds,
                            reason=(
                                "ultimate temporal activation requires exactly one matching "
                                "scheduled ultimate action at the same time and bar"
                            ),
                        )
                    )

            elif application.layer is EffectLayer.CONSUMABLE:
                matching = tuple(
                    action
                    for action in plan.actions
                    if action.kind is RotationActionKind.POTION
                    and abs(action.time_seconds - application.time_seconds) <= self._EPSILON
                    and action.name is not None
                    and self._stable_name(action.name) == self._stable_name(application.source)
                )
                if len(matching) != 1:
                    violations.append(
                        RotationPlanTemporalLegalityViolation(
                            effect_name=application.effect_name,
                            layer=application.layer,
                            source=application.source,
                            time_seconds=application.time_seconds,
                            reason=(
                                "consumable temporal activation requires exactly one matching "
                                "scheduled potion action at the same time"
                            ),
                        )
                    )

        return RotationPlanTemporalLegalityAssessment(
            applications=tuple(applications),
            violations=tuple(violations),
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @classmethod
    def _active_bar_before(
        cls,
        *,
        plan: RotationPlan,
        time_seconds: float,
        initial_bar: str,
    ) -> str:
        active = initial_bar
        for action in plan.actions:
            if action.time_seconds + cls._EPSILON >= time_seconds:
                break
            if action.kind is RotationActionKind.BAR_SWAP:
                active = str(action.bar)
        return active

    @staticmethod
    def _stable_name(value: object) -> str:
        return "".join(ch for ch in str(value or "").casefold() if ch.isalnum())

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = [
    "RotationPlanTemporalLegalityAssessment",
    "RotationPlanTemporalLegalityService",
    "RotationPlanTemporalLegalityViolation",
]
