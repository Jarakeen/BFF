from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_availability import (
    resolve_available_effects,
    resolve_ultimate_cast_effects,
)
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.passive_grant import PassiveGrant
from services.rotation_temporal_effect_uptime_service import (
    RotationTemporalEffectApplication,
)


@dataclass(frozen=True)
class RotationTemporalEffectLegalityViolation:
    effect_name: str
    layer: EffectLayer
    source: str
    time_seconds: float
    reason: str


@dataclass(frozen=True)
class RotationTemporalEffectLegalityAssessment:
    applications: tuple[RotationTemporalEffectApplication, ...]
    violations: tuple[RotationTemporalEffectLegalityViolation, ...]
    unresolved: tuple[str, ...]

    @property
    def is_legal(self) -> bool:
        return not self.violations and not self.unresolved


@dataclass(frozen=True)
class _ResolvedActivation:
    application: RotationTemporalEffectApplication
    effect: EffectVariant


class RotationTemporalEffectLegalityService:
    """Validate explicit temporal activations against canonical effect legality.

    This service intentionally answers a narrow question: given activations a
    caller claims actually occur, are their exact build effect identities,
    triggers, bars, and canonical cooldown spacing mechanically legal?

    It does not infer activations from chance/cooldown, does not decide when a
    proc should fire, and does not reconstruct the rotation's active bar at each
    timestamp. Plan-timeline bar legality is a separate scheduling concern.
    """

    _EPSILON = 1e-9

    def assess(
        self,
        *,
        build: CharacterBuild,
        applications: tuple[RotationTemporalEffectApplication, ...],
        passives: Iterable[PassiveGrant] = (),
    ) -> RotationTemporalEffectLegalityAssessment:
        passive_tuple = tuple(passives)
        unresolved: list[str] = []
        resolved: list[_ResolvedActivation] = []

        seen_applications: set[
            tuple[float, str, EffectLayer, str, str, str | None]
        ] = set()
        for application in applications:
            key = (
                float(application.time_seconds),
                application.effect_name.casefold(),
                application.layer,
                application.source.casefold(),
                application.bar,
                None if application.trigger is None else application.trigger.casefold(),
            )
            if key in seen_applications:
                raise ValueError(
                    "duplicate rotation temporal effect application: "
                    f"{application.effect_name!r} from {application.source!r} "
                    f"at {application.time_seconds:.3f}s"
                )
            seen_applications.add(key)

            matches = self._resolve_effect_matches(
                build=build,
                application=application,
                passives=passive_tuple,
            )
            if len(matches) != 1:
                if not matches:
                    unresolved.append(
                        f"no exact {application.layer.value} effect "
                        f"{application.effect_name!r} from {application.source!r} "
                        f"resolved on {application.bar} bar at "
                        f"{application.time_seconds:.3f}s"
                    )
                else:
                    unresolved.append(
                        f"multiple exact {application.layer.value} effect variants "
                        f"resolved for {application.effect_name!r} from "
                        f"{application.source!r} on {application.bar} bar at "
                        f"{application.time_seconds:.3f}s"
                    )
                continue

            effect = matches[0]
            if effect.cooldown is not None:
                cooldown = float(effect.cooldown)
                if not math.isfinite(cooldown) or cooldown < 0.0:
                    unresolved.append(
                        f"canonical cooldown is invalid for {effect.name!r} from "
                        f"{effect.source!r}: {effect.cooldown!r}"
                    )
                    continue
            resolved.append(_ResolvedActivation(application=application, effect=effect))

        violations = self._cooldown_violations(tuple(resolved))
        return RotationTemporalEffectLegalityAssessment(
            applications=tuple(applications),
            violations=violations,
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @classmethod
    def _cooldown_violations(
        cls,
        activations: tuple[_ResolvedActivation, ...],
    ) -> tuple[RotationTemporalEffectLegalityViolation, ...]:
        grouped: dict[tuple[str, EffectLayer, str], list[_ResolvedActivation]] = {}
        for activation in activations:
            application = activation.application
            key = (
                application.effect_name.casefold(),
                application.layer,
                application.source.casefold(),
            )
            grouped.setdefault(key, []).append(activation)

        violations: list[RotationTemporalEffectLegalityViolation] = []
        for group in grouped.values():
            ordered = sorted(group, key=lambda item: item.application.time_seconds)
            for previous, current in zip(ordered, ordered[1:]):
                cooldown = previous.effect.cooldown
                if cooldown is None or float(cooldown) <= 0.0:
                    continue
                gap = current.application.time_seconds - previous.application.time_seconds
                if gap + cls._EPSILON >= float(cooldown):
                    continue
                violations.append(
                    RotationTemporalEffectLegalityViolation(
                        effect_name=current.application.effect_name,
                        layer=current.application.layer,
                        source=current.application.source,
                        time_seconds=current.application.time_seconds,
                        reason=(
                            f"activation occurs {gap:.3f}s after the prior activation, "
                            f"inside the canonical {float(cooldown):.3f}s cooldown"
                        ),
                    )
                )
        return tuple(violations)

    @staticmethod
    def _resolve_effect_matches(
        *,
        build: CharacterBuild,
        application: RotationTemporalEffectApplication,
        passives: tuple[PassiveGrant, ...],
    ) -> tuple[EffectVariant, ...]:
        active_bar = BarId(application.bar)
        if application.layer == EffectLayer.ULTIMATE:
            candidates = resolve_ultimate_cast_effects(
                build,
                active_bar,
                trigger=application.trigger,
            )
        else:
            candidates = resolve_available_effects(build, active_bar, passives)

        return tuple(
            effect
            for effect in candidates
            if effect.name.casefold() == application.effect_name.casefold()
            and effect.layer == application.layer
            and effect.source.casefold() == application.source.casefold()
        )

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
    "RotationTemporalEffectLegalityAssessment",
    "RotationTemporalEffectLegalityService",
    "RotationTemporalEffectLegalityViolation",
]
