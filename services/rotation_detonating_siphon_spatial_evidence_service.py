from __future__ import annotations

"""Reviewed Detonating Siphon spatial facts without promoting disputed geometry."""

from dataclasses import dataclass
from enum import Enum

from services.rotation_runtime_output_eligibility_service import (
    DETONATING_SIPHON_GEOMETRY_CONDITION,
)
from services.rotation_runtime_spatial_condition_context_service import (
    RotationRuntimeSpatialCircleClause,
    RotationRuntimeSpatialConditionRule,
    RotationRuntimeSpatialSegmentClause,
)


class DetonatingSiphonAreaAnchor(str, Enum):
    CORPSE = "corpse"
    CASTER = "caster"


@dataclass(frozen=True)
class RotationDetonatingSiphonSpatialEvidence:
    """Reviewed U50-facing spatial evidence for Detonating Siphon.

    Radius and maximum tether range are supported by current skill reference data.
    The tooltip describes damage around the corpse plus enemies between caster and
    corpse, but observed live behavior has been reported with the area centered on
    the caster instead. That anchor conflict remains unresolved here. No reviewed
    corridor width is currently available either.
    """

    radius_meters: float = 5.0
    maximum_range_meters: float = 28.0
    area_anchor: DetonatingSiphonAreaAnchor | None = None
    tether_half_width_meters: float | None = None
    tooltip_geometry: str = (
        "enemies around the corpse and between the caster and corpse"
    )
    evidence: tuple[str, ...] = (
        "ESO-Hub current skill data: Detonating Siphon radius 5m, maximum range 28m, duration 20s",
        "ESO tooltip wording places the area around the corpse and includes the caster-to-corpse tether",
        "community reproduction reports live area damage may be centered on the caster instead of the corpse",
        "Update 50 live patch notes reviewed with no Detonating Siphon geometry change identified",
    )
    unresolved: tuple[str, ...] = (
        "Detonating Siphon live area anchor is unresolved: tooltip says corpse-centered, observed testing reports caster-centered behavior",
        "Detonating Siphon tether corridor width is unresolved",
    )

    @property
    def executable(self) -> bool:
        return self.area_anchor is not None and self.tether_half_width_meters is not None


class RotationDetonatingSiphonSpatialEvidenceService:
    """Expose reviewed Siphon facts and build geometry only from explicit resolved evidence.

    This service deliberately does not guess the disputed area anchor or tether width.
    ``rule(...)`` returns ``None`` until both are supplied explicitly by the caller.
    That keeps the generic spatial runtime usable while production Siphon output stays
    fail-closed.
    """

    def evidence(self) -> RotationDetonatingSiphonSpatialEvidence:
        return RotationDetonatingSiphonSpatialEvidence()

    def rule(
        self,
        *,
        area_anchor: DetonatingSiphonAreaAnchor | str | None,
        tether_half_width_meters: float | None,
        caster_entity_id: str = "caster",
        corpse_entity_id: str = "corpse",
        target_entity_id: str = "target",
    ) -> RotationRuntimeSpatialConditionRule | None:
        if area_anchor is None or tether_half_width_meters is None:
            return None

        anchor = (
            area_anchor
            if isinstance(area_anchor, DetonatingSiphonAreaAnchor)
            else DetonatingSiphonAreaAnchor(str(area_anchor).strip().casefold())
        )
        half_width = float(tether_half_width_meters)
        if half_width < 0.0:
            raise ValueError("Detonating Siphon tether half-width cannot be negative")

        center_entity_id = (
            corpse_entity_id
            if anchor is DetonatingSiphonAreaAnchor.CORPSE
            else caster_entity_id
        )
        evidence = self.evidence()
        return RotationRuntimeSpatialConditionRule(
            condition=DETONATING_SIPHON_GEOMETRY_CONDITION,
            clauses=(
                RotationRuntimeSpatialCircleClause(
                    center_entity_id=center_entity_id,
                    target_entity_id=target_entity_id,
                    maximum_distance=evidence.radius_meters,
                ),
                RotationRuntimeSpatialSegmentClause(
                    start_entity_id=caster_entity_id,
                    end_entity_id=corpse_entity_id,
                    target_entity_id=target_entity_id,
                    half_width=half_width,
                ),
            ),
            source=(
                "reviewed Detonating Siphon spatial evidence with explicit caller-resolved "
                f"area anchor={anchor.value} and tether half-width={half_width:g}m"
            ),
        )


__all__ = [
    "DetonatingSiphonAreaAnchor",
    "RotationDetonatingSiphonSpatialEvidence",
    "RotationDetonatingSiphonSpatialEvidenceService",
]
