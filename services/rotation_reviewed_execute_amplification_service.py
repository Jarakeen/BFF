from __future__ import annotations

"""Reviewed runtime interpolation for continuous target-Health execute bonuses.

Generic ``up to N% more damage`` text is not enough to infer interpolation.  This
service contains only source-reviewed skill semantics.  Skills absent from the
reviewed table remain unresolved by callers.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RotationReviewedExecuteAmplification:
    skill_name: str
    scaling: str
    evidence: str


@dataclass(frozen=True)
class RotationReviewedExecuteAmplificationResult:
    damage_multiplier: float | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.damage_multiplier is not None and not self.unresolved


_REVIEWED = {
    "killer's blade": RotationReviewedExecuteAmplification(
        skill_name="Killer's Blade",
        scaling="linear_from_threshold_to_zero_health",
        evidence=(
            "ESO-Hub Killer's Blade morph text: scales linearly based on missing Health; "
            "tooltip: up to 400% more damage below 50% Health"
        ),
    ),
}


class RotationReviewedExecuteAmplificationService:
    """Resolve reviewed continuous execute amplification without generic inference."""

    def semantics(self, skill_name: str) -> RotationReviewedExecuteAmplification | None:
        return _REVIEWED.get(str(skill_name or "").strip().casefold())

    def resolve_multiplier(
        self,
        *,
        skill_name: str,
        health_fraction: float,
        threshold: float,
        maximum_bonus_fraction: float | None,
    ) -> RotationReviewedExecuteAmplificationResult:
        reviewed = self.semantics(skill_name)
        if reviewed is None:
            return RotationReviewedExecuteAmplificationResult(
                damage_multiplier=None,
                unresolved=(
                    f"{skill_name}: continuous execute interpolation is not source-reviewed",
                ),
            )
        if reviewed.scaling != "linear_from_threshold_to_zero_health":
            return RotationReviewedExecuteAmplificationResult(
                damage_multiplier=None,
                unresolved=(
                    f"{skill_name}: reviewed execute scaling kind is unsupported: {reviewed.scaling}",
                ),
            )
        health = float(health_fraction)
        start = float(threshold)
        if not math.isfinite(health) or health < 0.0 or health > 1.0:
            raise ValueError("execute target Health fraction must be finite within [0, 1]")
        if not math.isfinite(start) or start <= 0.0 or start > 1.0:
            raise ValueError("execute threshold must be finite within (0, 1]")
        if maximum_bonus_fraction is None:
            return RotationReviewedExecuteAmplificationResult(
                damage_multiplier=None,
                unresolved=(
                    f"{skill_name}: reviewed execute interpolation requires maximum bonus evidence",
                ),
            )
        maximum = float(maximum_bonus_fraction)
        if not math.isfinite(maximum) or maximum < 0.0:
            raise ValueError("execute maximum bonus fraction must be finite and non-negative")

        if health >= start:
            return RotationReviewedExecuteAmplificationResult(damage_multiplier=1.0)

        progress = (start - health) / start
        progress = min(1.0, max(0.0, progress))
        return RotationReviewedExecuteAmplificationResult(
            damage_multiplier=1.0 + maximum * progress,
        )


__all__ = [
    "RotationReviewedExecuteAmplification",
    "RotationReviewedExecuteAmplificationResult",
    "RotationReviewedExecuteAmplificationService",
]
