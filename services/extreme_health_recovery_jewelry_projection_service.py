from __future__ import annotations

"""Compatibility wrapper for the shared Extreme Recovery jewelry projection."""

from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from services.extreme_recovery_jewelry_projection_service import (
    ExtremeRecoveryJewelryProjection,
    ExtremeRecoveryJewelryProjectionService,
)


ExtremeHealthRecoveryJewelryProjection = ExtremeRecoveryJewelryProjection


class ExtremeHealthRecoveryJewelryProjectionService:
    """Backward-compatible Health Recovery adapter over the shared Recovery owner."""

    def __init__(
        self,
        glyph_repository: JewelryGlyphEffectRepository,
        trait_repository: JewelryTraitRepository,
    ) -> None:
        self._shared = ExtremeRecoveryJewelryProjectionService(
            glyph_repository,
            trait_repository,
        )

    def build(self) -> ExtremeHealthRecoveryJewelryProjection:
        return self._shared.build("health_recovery")


__all__ = [
    "ExtremeHealthRecoveryJewelryProjection",
    "ExtremeHealthRecoveryJewelryProjectionService",
]
