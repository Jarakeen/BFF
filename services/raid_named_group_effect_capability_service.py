from __future__ import annotations

"""Project canonical named group effects into raid Coverage presentation.

Coverage's original profile intentionally mapped only a small reviewed subset of
EffectVariant identities. The raid-facing catalog is broader, but its display labels
still correspond directly to canonical snake_case identities for named Major/Minor,
status, enchant, and other group effects.

This service makes only that exact identity bridge. It does not infer aliases, source
semantics, or uptime. Self-only effects are excluded so a personal potion/buff never
masquerades as raid coverage. Unclassified targets remain unverified rather than guessed.
"""

from typing import Iterable

from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.raid_group_effect_catalog import GROUP_COVERAGE_NAMES
from services.saved_build_capability_service import RaidCoverageSnapshot


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _canonical_key(display_name: str) -> str:
    return "_".join(_clean(display_name).casefold().replace("'", "").split())


_DISPLAY_BY_CANONICAL = {
    _canonical_key(display_name): display_name for display_name in GROUP_COVERAGE_NAMES
}
_ALLOWED_TARGETS = {
    SupportTargetType.ALLY,
    SupportTargetType.SELF_OR_ALLY,
    SupportTargetType.GROUP,
    SupportTargetType.ENEMY,
}


def _provider_label(build: PlayerBuild) -> str:
    return _clean(build.Name or build.Gamertag or build.BuildName) or "Unnamed"


class RaidNamedGroupEffectCapabilityService:
    """Overlay exact canonical group-effect identities onto Coverage evidence."""

    def overlay(
        self,
        snapshot: RaidCoverageSnapshot,
        builds: Iterable[PlayerBuild],
        *,
        capability_service,
    ) -> RaidCoverageSnapshot:
        status = dict(snapshot.status)
        providers = {name: list(values) for name, values in snapshot.providers.items()}
        conditional = {
            name: list(values)
            for name, values in snapshot.conditional_providers.items()
        }

        for build in tuple(builds):
            if not isinstance(build, PlayerBuild):
                raise TypeError("named raid-effect capability requires PlayerBuild values")
            audit = capability_service.audit_build(build)
            provider = _provider_label(build)
            for effect in tuple(audit.resolved_effects or ()):
                display_name = _DISPLAY_BY_CANONICAL.get(_clean(effect.name).casefold())
                if display_name is None:
                    continue
                if effect.target_type not in _ALLOWED_TARGETS:
                    continue

                status.setdefault(display_name, "unverified")
                providers.setdefault(display_name, [])
                conditional.setdefault(display_name, [])
                is_conditional = bool(
                    effect.condition
                    or effect.trigger
                    or not bool(getattr(effect, "eligible", True))
                )
                bucket = conditional[display_name] if is_conditional else providers[display_name]
                if provider not in bucket:
                    bucket.append(provider)

        for name in tuple(status):
            if providers.get(name):
                status[name] = "available"
            elif conditional.get(name):
                status[name] = "conditional"

        return RaidCoverageSnapshot(status, providers, conditional)


__all__ = ["RaidNamedGroupEffectCapabilityService"]
