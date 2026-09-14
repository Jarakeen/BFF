from __future__ import annotations

"""Bind one Raid Plan chair into canonical Rotation Generate context.

The page owns Raid Plan selection. The saved-build resolver proves the exact reusable
build. The canonical context then freezes that exact build and carries only the chair's
encounter-scoped triggered responsibilities. This adapter does not inspect Qt widgets and
does not materialize runtime-triggered plan intent into scheduled RotationAction rows.
"""

from typing import Iterable

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan
from services.raid_plan_saved_build_resolution_service import (
    RaidPlanSavedBuildResolutionService,
)
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext


class RaidPlanRotationContextBridge:
    def __init__(
        self,
        *,
        saved_build_resolution: RaidPlanSavedBuildResolutionService | None = None,
    ) -> None:
        self.saved_build_resolution = (
            saved_build_resolution or RaidPlanSavedBuildResolutionService()
        )

    def bind(
        self,
        *,
        base_context: RotationGenerateCanonicalContext,
        raid_plan: RaidPlan,
        seat_id: str,
        saved_builds: Iterable[PlayerBuild],
        encounter_id: str,
        adjustment_labels: tuple[str, ...] = (),
        provenance: tuple[str, ...] = (),
    ) -> RotationGenerateCanonicalContext:
        if not isinstance(base_context, RotationGenerateCanonicalContext):
            raise TypeError("Raid Plan Rotation bridge requires canonical Generate context")

        resolution = self.saved_build_resolution.resolve(
            raid_plan=raid_plan,
            seat_id=seat_id,
            saved_builds=saved_builds,
        )
        if not resolution.resolved or resolution.build is None:
            detail = "; ".join(resolution.unresolved) or "saved build ownership unresolved"
            raise ValueError(
                "Raid Plan seat cannot enter Rotation Generate: " + detail
            )

        return base_context.with_raid_plan_member(
            raid_plan=raid_plan,
            seat_id=resolution.seat_id,
            build=resolution.build,
            encounter_id=encounter_id,
            adjustment_labels=adjustment_labels,
            provenance=provenance,
        )


__all__ = ["RaidPlanRotationContextBridge"]
