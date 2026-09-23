from __future__ import annotations

"""Project proven Objective #32 runtime-effect topology into potion-cooldown evidence."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from services.extreme_sustained_dps_potion_cooldown_resolution_service import (
    ExtremeSustainedDPSPotionCooldownScenarioEvidence,
)
from services.rotation_potion_cooldown_effect_variant_service import (
    POTION_COOLDOWN_REDUCTION_EFFECT,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionCooldownRuntimeEvidence:
    scenario: ExtremeSustainedDPSPotionCooldownScenarioEvidence
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSPotionCooldownRuntimeEvidenceService:
    """Extract cooldown effects only from a proven-complete runtime effect universe."""

    @classmethod
    def resolve(
        cls,
        *,
        effects: tuple[EffectVariant, ...],
        denominator_proven: bool,
        unresolved: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSPotionCooldownRuntimeEvidence:
        blockers = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )
        cooldown_effects = tuple(
            effect
            for effect in effects
            if str(getattr(effect, "name", "") or "").strip().casefold()
            == POTION_COOLDOWN_REDUCTION_EFFECT.casefold()
        )
        complete = bool(denominator_proven and not blockers)
        scenario = ExtremeSustainedDPSPotionCooldownScenarioEvidence(
            effects=cooldown_effects,
            complete=complete,
        )
        return ExtremeSustainedDPSPotionCooldownRuntimeEvidence(
            scenario=scenario,
            evidence=(
                f"Runtime effects inspected for potion cooldown: {len(effects)}",
                f"Potion cooldown effects retained: {len(cooldown_effects)}",
                (
                    "Potion cooldown runtime-effect denominator is proven complete"
                    if complete
                    else "Potion cooldown runtime-effect denominator remains open"
                ),
            ),
            unresolved=(
                blockers
                if blockers
                else (
                    ()
                    if denominator_proven
                    else ("Runtime effect denominator is not proven complete",)
                )
            ),
        )


__all__ = [
    "ExtremeSustainedDPSPotionCooldownRuntimeEvidence",
    "ExtremeSustainedDPSPotionCooldownRuntimeEvidenceService",
]
