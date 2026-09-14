from __future__ import annotations

"""Compatibility wrapper for the shared Extreme Recovery Champion Point classifier."""

from minmax.champion_point_static_repository import ChampionPointRecord
from services.extreme_recovery_champion_point_branch_service import (
    ExtremeRecoveryChampionPointBranch,
    ExtremeRecoveryChampionPointBranchKind,
    ExtremeRecoveryChampionPointBranchService,
)


ExtremeHealthRecoveryChampionPointBranch = ExtremeRecoveryChampionPointBranch
ExtremeHealthRecoveryChampionPointBranchKind = ExtremeRecoveryChampionPointBranchKind


class ExtremeHealthRecoveryChampionPointBranchService:
    """Backward-compatible Health Recovery adapter over the shared Recovery owner."""

    @classmethod
    def classify(
        cls,
        record: ChampionPointRecord,
    ) -> ExtremeHealthRecoveryChampionPointBranch:
        return ExtremeRecoveryChampionPointBranchService.classify(
            record,
            "health_recovery",
        )


__all__ = [
    "ExtremeHealthRecoveryChampionPointBranch",
    "ExtremeHealthRecoveryChampionPointBranchKind",
    "ExtremeHealthRecoveryChampionPointBranchService",
]
