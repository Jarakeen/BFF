from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OptimizationMode(str, Enum):
    AUDIT = "audit"
    BUILD = "build"
    RECRUIT = "recruit"
    COMPARE = "compare"


@dataclass(frozen=True)
class OptimizationModePolicy:
    mode: OptimizationMode
    title: str
    action_label: str
    uses_two_teams: bool
    allows_saved_players: bool
    allows_recruitment: bool
    ranks_result: bool


_MODE_POLICIES = {
    OptimizationMode.AUDIT: OptimizationModePolicy(
        mode=OptimizationMode.AUDIT,
        title="Audit Current Team",
        action_label="Audit Team",
        uses_two_teams=False,
        allows_saved_players=True,
        allows_recruitment=False,
        ranks_result=False,
    ),
    OptimizationMode.BUILD: OptimizationModePolicy(
        mode=OptimizationMode.BUILD,
        title="Optimize Team",
        action_label="Optimize Team",
        uses_two_teams=False,
        allows_saved_players=True,
        allows_recruitment=True,
        ranks_result=True,
    ),
    OptimizationMode.RECRUIT: OptimizationModePolicy(
        mode=OptimizationMode.RECRUIT,
        title="Recruitment Plan",
        action_label="Generate Recruitment Plan",
        uses_two_teams=False,
        allows_saved_players=False,
        allows_recruitment=True,
        ranks_result=False,
    ),
    OptimizationMode.COMPARE: OptimizationModePolicy(
        mode=OptimizationMode.COMPARE,
        title="Compare Teams",
        action_label="Compare Teams",
        uses_two_teams=True,
        allows_saved_players=True,
        allows_recruitment=True,
        ranks_result=True,
    ),
}


def policy_for_mode(mode: OptimizationMode) -> OptimizationModePolicy:
    return _MODE_POLICIES[mode]
