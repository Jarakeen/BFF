from dataclasses import dataclass


@dataclass(frozen=True)
class DDMitigationResult:
    """Resolved target mitigation for a DD damage event."""

    target_resistance: float
    penetration: float
    remaining_resistance: float
    mitigation_fraction: float
    damage_multiplier: float


def calculate_dd_mitigation(
    *,
    target_resistance: float,
    penetration: float,
    resistance_per_percent: float = 500.0,
) -> DDMitigationResult:
    """Calculate PvE target mitigation from resistance."""

    if target_resistance < 0:
        raise ValueError(
            "Target resistance cannot be negative."
        )

    if penetration < 0:
        raise ValueError(
            "Penetration cannot be negative."
        )

    if resistance_per_percent <= 0:
        raise ValueError(
            "Resistance conversion must be positive."
        )

    remaining_resistance = max(
        0.0,
        target_resistance - penetration,
    )

    mitigation_fraction = (
        remaining_resistance
        / resistance_per_percent
        / 100.0
    )

    mitigation_fraction = min(
        1.0,
        mitigation_fraction,
    )

    damage_multiplier = 1.0 - mitigation_fraction

    return DDMitigationResult(
        target_resistance=target_resistance,
        penetration=penetration,
        remaining_resistance=remaining_resistance,
        mitigation_fraction=mitigation_fraction,
        damage_multiplier=damage_multiplier,
    )