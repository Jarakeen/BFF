from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RotationHealerExternalConditionalHealingEvidence:
    """Reviewed healer consequence whose actual healing is triggered externally.

    ``reviewed_magnitude`` retains the source wording's numeric magnitude without
    turning it into a scheduled heal event. ``magnitude_unit`` and
    ``trigger_condition`` keep the semantic boundary explicit until runtime
    trigger cadence/ownership is separately proven.
    """

    skill_id: str
    effect_name: str
    duration_seconds: float
    reviewed_magnitude: float
    magnitude_unit: str
    trigger_condition: str
    provenance: tuple[str, ...]
    game_version: str


class RotationHealerExternalConditionalHealingService:
    """Expose explicitly reviewed external-condition healer evidence by semantic id."""

    _U50 = {
        "overflowing_altar": RotationHealerExternalConditionalHealingEvidence(
            skill_id="overflowing_altar",
            effect_name="minor_lifesteal",
            duration_seconds=30.0,
            reviewed_magnitude=600.0,
            magnitude_unit="health_per_second",
            trigger_condition="damage_affected_enemy",
            provenance=(
                "reviewed U50 Overflowing Altar effect: Minor Lifesteal for 30 seconds",
                "reviewed U50 Minor Lifesteal magnitude: 600 Health per second when the affected enemy is damaged",
                "Blood Feast synergy healing remains ally-synergy-owned and is not caster action healing",
            ),
            game_version="U50",
        ),
    }

    def resolve(
        self,
        skill_id: str,
        *,
        game_version: str = "U50",
    ) -> RotationHealerExternalConditionalHealingEvidence | None:
        canonical = str(skill_id or "").strip().casefold()
        version = str(game_version or "").strip()
        if version != "U50":
            return None
        return self._U50.get(canonical)


__all__ = [
    "RotationHealerExternalConditionalHealingEvidence",
    "RotationHealerExternalConditionalHealingService",
]
