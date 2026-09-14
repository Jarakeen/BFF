from __future__ import annotations

"""Resolve one Raid Plan chair to one exact reusable saved build.

Raid Plan owns trial-specific selection; saved-build storage owns reusable build state.
This service joins those identities without reading UI widgets or broadening an ambiguous
selection. Callers receive an isolated PlayerBuild copy suitable for freezing into an
EffectiveBuildSnapshot.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _clean(value).casefold()


@dataclass(frozen=True)
class RaidPlanSavedBuildResolution:
    seat_id: str
    build: PlayerBuild | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.build is not None and not self.unresolved


class RaidPlanSavedBuildResolutionService:
    """Resolve one exact selected Raid Plan build from reusable saved builds."""

    def resolve(
        self,
        *,
        raid_plan: RaidPlan,
        seat_id: str,
        saved_builds: Iterable[PlayerBuild],
    ) -> RaidPlanSavedBuildResolution:
        if not isinstance(raid_plan, RaidPlan):
            raise TypeError("raid plan saved-build resolution requires RaidPlan")

        seat = _clean(seat_id)
        if not seat:
            raise ValueError("raid plan saved-build resolution requires seat_id")

        member = raid_plan.member(seat)
        if member is None:
            return RaidPlanSavedBuildResolution(
                seat_id=seat,
                unresolved=(f"Raid Plan seat {seat!r} is not present",),
            )

        selected_build = _clean(member.selected_build_name)
        if not selected_build:
            return RaidPlanSavedBuildResolution(
                seat_id=member.seat_id,
                unresolved=(
                    f"Raid Plan seat {member.seat_id!r} has no selected build",
                ),
            )

        candidates: list[PlayerBuild] = []
        for build in tuple(saved_builds):
            if not isinstance(build, PlayerBuild):
                continue
            if _key(build.BuildName) != _key(selected_build):
                continue
            if member.character_name and _key(build.Name) != _key(member.character_name):
                continue
            if member.gamertag and _key(build.Gamertag) != _key(member.gamertag):
                continue
            candidates.append(build)

        if not candidates:
            identity = " / ".join(
                part
                for part in (
                    member.gamertag,
                    member.character_name or "",
                    selected_build,
                )
                if _clean(part)
            )
            return RaidPlanSavedBuildResolution(
                seat_id=member.seat_id,
                unresolved=(
                    f"No saved build matches Raid Plan seat {member.seat_id!r}: {identity}",
                ),
            )

        if len(candidates) > 1:
            return RaidPlanSavedBuildResolution(
                seat_id=member.seat_id,
                unresolved=(
                    f"Multiple saved builds match Raid Plan seat {member.seat_id!r}; exact build ownership is ambiguous",
                ),
            )

        return RaidPlanSavedBuildResolution(
            seat_id=member.seat_id,
            build=deepcopy(candidates[0]),
        )


__all__ = [
    "RaidPlanSavedBuildResolution",
    "RaidPlanSavedBuildResolutionService",
]
