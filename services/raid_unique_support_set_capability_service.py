from __future__ import annotations

"""Project exact equipped support-set presence into static Coverage evidence.

The canonical saved-build capability audit remains authoritative for canonical
EffectVariant mechanics. Unique raid-support sets are a separate reviewed planning
catalog because several of their group effects are not Major/Minor named effects and
therefore do not yet map cleanly to EffectVariant identity.

This service makes one deliberately narrow claim: when the exact saved build has the
reviewed set-piece threshold active on at least one bar, the build has static capability
to produce that support-set effect. Triggered/proc effects remain ``conditional``;
this service never claims uptime.
"""

from dataclasses import dataclass
from typing import Iterable

from models.build_model import PlayerBuild
from services.raid_unique_support_set_catalog import UNIQUE_SUPPORT_SET_EFFECTS
from services.saved_build_capability_service import (
    RaidCoverageSnapshot,
    SavedBuildCapabilityService,
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _provider_label(build: PlayerBuild) -> str:
    return _clean(build.Name or build.Gamertag or build.BuildName) or "Unnamed"


def _set_count(build: PlayerBuild, bar: str, set_name: str) -> int:
    target = _clean(set_name).casefold()
    counts = SavedBuildCapabilityService._active_set_counts(build, bar)
    for name, pieces in counts.items():
        if _clean(name).casefold() == target:
            return int(pieces)
    return 0


@dataclass(frozen=True)
class RaidUniqueSupportSetCapabilityEvidence:
    effect_name: str
    provider: str
    state: str
    qualifying_bars: tuple[str, ...]
    front_pieces: int
    back_pieces: int

    def __post_init__(self) -> None:
        if self.state not in {"available", "conditional"}:
            raise ValueError("unique support-set capability state must be available or conditional")
        if not self.qualifying_bars:
            raise ValueError("unique support-set capability evidence requires a qualifying bar")


class RaidUniqueSupportSetCapabilityService:
    """Resolve reviewed support-set presence from exact saved-build equipment."""

    def evaluate(
        self,
        builds: Iterable[PlayerBuild],
    ) -> tuple[RaidUniqueSupportSetCapabilityEvidence, ...]:
        evidence: list[RaidUniqueSupportSetCapabilityEvidence] = []
        for build in tuple(builds):
            if not isinstance(build, PlayerBuild):
                raise TypeError("unique support-set capability requires PlayerBuild values")
            provider = _provider_label(build)
            for reference in UNIQUE_SUPPORT_SET_EFFECTS:
                front = _set_count(build, "front", reference.name)
                back = _set_count(build, "back", reference.name)
                qualifying = tuple(
                    bar
                    for bar, pieces in (("front", front), ("back", back))
                    if pieces >= reference.required_pieces
                )
                if not qualifying:
                    continue
                evidence.append(
                    RaidUniqueSupportSetCapabilityEvidence(
                        effect_name=reference.name,
                        provider=provider,
                        state=reference.static_state,
                        qualifying_bars=qualifying,
                        front_pieces=front,
                        back_pieces=back,
                    )
                )
        return tuple(evidence)

    def overlay(
        self,
        snapshot: RaidCoverageSnapshot,
        builds: Iterable[PlayerBuild],
    ) -> RaidCoverageSnapshot:
        """Add reviewed unique-set presence without weakening stronger evidence."""
        status = dict(snapshot.status)
        providers = {name: list(values) for name, values in snapshot.providers.items()}
        conditional = {
            name: list(values)
            for name, values in snapshot.conditional_providers.items()
        }

        for item in self.evaluate(builds):
            status.setdefault(item.effect_name, "unverified")
            providers.setdefault(item.effect_name, [])
            conditional.setdefault(item.effect_name, [])
            bucket = (
                providers[item.effect_name]
                if item.state == "available"
                else conditional[item.effect_name]
            )
            if item.provider not in bucket:
                bucket.append(item.provider)

        for name in tuple(status):
            if providers.get(name):
                status[name] = "available"
            elif conditional.get(name):
                status[name] = "conditional"

        return RaidCoverageSnapshot(status, providers, conditional)


__all__ = [
    "RaidUniqueSupportSetCapabilityEvidence",
    "RaidUniqueSupportSetCapabilityService",
]
