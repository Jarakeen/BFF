from __future__ import annotations

from services.rotation_dd_dot_runtime_service import RotationDDDotRuntimeEvidence


WINTERS_REVENGE_SOURCE = "Winter's Revenge"


def u50_winters_revenge_runtime_evidence(
    *,
    coefficient_number: int,
) -> RotationDDDotRuntimeEvidence:
    """Return reviewed U50 runtime timing for Winter's Revenge.

    Evidence boundary:
    - BTVTools' U50 skill database reports 12s duration and 1s AoE DoT ticks.
    - Historical ESO forum observation reports no immediate cast-time tick and
      damage beginning after roughly one second.
    - Refresh/overwrite behavior is *not* claimed by those sources here, so
      repeated applications remain unresolved until separate evidence proves it.

    ``coefficient_number`` is supplied by the canonical component seed rather
    than hard-coded because the runtime catalog owns timing, not coefficient
    identity reconciliation.
    """

    return RotationDDDotRuntimeEvidence(
        source_name=WINTERS_REVENGE_SOURCE,
        coefficient_number=int(coefficient_number),
        duration_seconds=12.0,
        tick_interval_seconds=1.0,
        first_tick_offset_seconds=1.0,
        tick_on_expiry_boundary=True,
        refresh_behavior_verified=False,
        provenance=(
            "BTVTools Winter's Revenge skill database; U50 data as of 2026-09-07; duration=12s; AoE DoT=1s ticks",
            "ESO official forum historical observation: Winter's Revenge no longer has an initial tick; damage begins after about 1s",
        ),
    )
