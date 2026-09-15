from __future__ import annotations

"""Resolve one RaidPlan into the exact static-build scope Coverage may inspect.

This integration service does not calculate coverage and does not infer provider ownership.
It resolves only explicitly selected saved builds, preserves unresolved chair evidence, and
projects exact assignment-label matches for Coverage presentation. Primary and secondary
assignment labels remain raid-lead planning intent, not proof of effect uptime.
"""

from dataclasses import dataclass
from typing import Iterable

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan
from services.raid_plan_saved_build_resolution_service import (
    RaidPlanSavedBuildResolutionService,
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _clean(value).casefold()


@dataclass(frozen=True)
class RaidPlanCoverageMember:
    seat_id: str
    player_label: str
    build: PlayerBuild


@dataclass(frozen=True)
class RaidPlanCoverageScope:
    plan_id: str
    plan_name: str
    trial_id: str
    total_chairs: int
    named_members: int
    members: tuple[RaidPlanCoverageMember, ...]
    unresolved: tuple[str, ...]
    primary_providers: tuple[tuple[str, tuple[str, ...]], ...]
    secondary_providers: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def resolved_builds(self) -> tuple[PlayerBuild, ...]:
        return tuple(row.build for row in self.members)

    def primary_for(self, effect_name: str) -> tuple[str, ...]:
        wanted = _key(effect_name)
        return next((values for key, values in self.primary_providers if key == wanted), ())

    def secondary_for(self, effect_name: str) -> tuple[str, ...]:
        wanted = _key(effect_name)
        return next((values for key, values in self.secondary_providers if key == wanted), ())


class RaidPlanCoverageScopeService:
    """Resolve exact Raid Plan build scope and explicit coverage-assignment labels."""

    def __init__(self, resolver: RaidPlanSavedBuildResolutionService | None = None) -> None:
        self.resolver = resolver or RaidPlanSavedBuildResolutionService()

    def compose(
        self,
        *,
        raid_plan: RaidPlan,
        saved_builds: Iterable[PlayerBuild],
        coverage_effect_names: Iterable[str],
        total_chairs: int = 12,
    ) -> RaidPlanCoverageScope:
        if not isinstance(raid_plan, RaidPlan):
            raise TypeError("raid plan coverage scope requires RaidPlan")

        saved = tuple(saved_builds)
        effect_labels = {
            _key(name): _clean(name)
            for name in coverage_effect_names
            if _clean(name)
        }
        members: list[RaidPlanCoverageMember] = []
        unresolved: list[str] = []
        primary: dict[str, list[str]] = {key: [] for key in effect_labels}
        secondary: dict[str, list[str]] = {key: [] for key in effect_labels}

        for member in raid_plan.members:
            player_label = member.character_name or member.gamertag or member.seat_id
            result = self.resolver.resolve(
                raid_plan=raid_plan,
                seat_id=member.seat_id,
                saved_builds=saved,
            )
            if result.resolved and result.build is not None:
                members.append(
                    RaidPlanCoverageMember(
                        seat_id=member.seat_id,
                        player_label=player_label,
                        build=result.build,
                    )
                )
            else:
                unresolved.extend(result.unresolved)

            primary_key = _key(member.primary_assignment)
            if primary_key in primary:
                primary[primary_key].append(player_label)
            secondary_key = _key(member.secondary_assignment)
            if secondary_key in secondary:
                secondary[secondary_key].append(player_label)

        return RaidPlanCoverageScope(
            plan_id=raid_plan.plan_id,
            plan_name=raid_plan.name,
            trial_id=raid_plan.trial_id,
            total_chairs=int(total_chairs),
            named_members=len(raid_plan.members),
            members=tuple(members),
            unresolved=tuple(dict.fromkeys(unresolved)),
            primary_providers=tuple(
                (key, tuple(values)) for key, values in primary.items() if values
            ),
            secondary_providers=tuple(
                (key, tuple(values)) for key, values in secondary.items() if values
            ),
        )


__all__ = [
    "RaidPlanCoverageMember",
    "RaidPlanCoverageScope",
    "RaidPlanCoverageScopeService",
]
