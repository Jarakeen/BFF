from __future__ import annotations

"""Resolve activated runtime intent into legal execution-strategy candidates.

This boundary chooses only already-proven slotted capability sources. It does not
schedule RotationAction objects, choose a concrete execution time beyond preserving the
trigger activation time, infer a bar swap, or decide whether an occupied action may be
interrupted. Those concerns remain with later execution-legality/materialization stages.
"""

from dataclasses import dataclass

from models.build_model import PlayerBuild
from services.rotation_runtime_trigger_condition_service import RotationRuntimeActivatedIntent
from services.saved_build_utility_capability_service import (
    SavedBuildUtilityCapabilityService,
    SavedBuildUtilityProviderSource,
    SavedBuildUtilityProviderSourceResolution,
)


def _clean(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class RotationRuntimeExecutionStrategyCandidate:
    """One exact slotted capability source that may satisfy an activated intent."""

    intent_id: str
    activated_at_seconds: float
    directive: str
    capability_type: str
    skill_name: str
    bar: str
    target_key: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("intent_id", "directive", "capability_type", "skill_name"):
            value = _clean(getattr(self, field_name))
            if not value:
                raise ValueError(f"runtime execution strategy {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        bar = _clean(self.bar).casefold()
        if bar not in {"front", "back"}:
            raise ValueError("runtime execution strategy bar must be front or back")
        object.__setattr__(self, "bar", bar)
        object.__setattr__(self, "capability_type", self.capability_type.casefold())
        if self.target_key is not None:
            target = _clean(self.target_key)
            object.__setattr__(self, "target_key", target or None)


@dataclass(frozen=True)
class RotationRuntimeExecutionStrategyResolution:
    activated_intent: RotationRuntimeActivatedIntent
    candidates: tuple[RotationRuntimeExecutionStrategyCandidate, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.candidates) and not self.unresolved


class RotationRuntimeExecutionStrategyService:
    """Use canonical saved-build capability evidence to expose legal strategy choices."""

    def __init__(self, capability_service: SavedBuildUtilityCapabilityService | object) -> None:
        provider = getattr(capability_service, "provider_sources_for", None)
        if not callable(provider):
            raise TypeError("runtime execution strategy requires provider_sources_for(build, capability_type)")
        self.capability_service = capability_service

    def resolve(
        self,
        *,
        activated_intent: RotationRuntimeActivatedIntent,
        build: PlayerBuild,
    ) -> RotationRuntimeExecutionStrategyResolution:
        if not isinstance(activated_intent, RotationRuntimeActivatedIntent):
            raise TypeError("runtime execution strategy requires RotationRuntimeActivatedIntent")
        if not isinstance(build, PlayerBuild):
            raise TypeError("runtime execution strategy requires PlayerBuild")

        intent = activated_intent.intent
        capability = _clean(intent.required_capability_type).casefold()
        if not capability:
            return RotationRuntimeExecutionStrategyResolution(
                activated_intent=activated_intent,
                unresolved=(
                    "activated runtime intent has no required capability type for action selection",
                ),
            )

        resolution = self.capability_service.provider_sources_for(
            build=build,
            capability_type=capability,
        )
        if not isinstance(resolution, SavedBuildUtilityProviderSourceResolution):
            raise TypeError(
                "provider_sources_for returned unsupported runtime capability resolution"
            )

        candidates = tuple(
            self._candidate(activated_intent, source)
            for source in resolution.sources
        )
        unresolved = tuple(resolution.unresolved)
        if not candidates and not unresolved:
            unresolved = (
                f"saved build has no slotted canonical {capability} provider",
            )

        return RotationRuntimeExecutionStrategyResolution(
            activated_intent=activated_intent,
            candidates=candidates,
            unresolved=unresolved,
        )

    @staticmethod
    def _candidate(
        activated_intent: RotationRuntimeActivatedIntent,
        source: SavedBuildUtilityProviderSource,
    ) -> RotationRuntimeExecutionStrategyCandidate:
        intent = activated_intent.intent
        return RotationRuntimeExecutionStrategyCandidate(
            intent_id=intent.intent_id,
            activated_at_seconds=activated_intent.activated_at_seconds,
            directive=intent.directive,
            capability_type=source.capability_type,
            skill_name=source.skill_name,
            bar=source.bar,
            target_key=intent.target_key,
        )


__all__ = [
    "RotationRuntimeExecutionStrategyCandidate",
    "RotationRuntimeExecutionStrategyResolution",
    "RotationRuntimeExecutionStrategyService",
]
