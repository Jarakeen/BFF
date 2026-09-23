from __future__ import annotations

"""Derive canonical passive-grant evidence for generated Extreme progression.

Only potion-cooldown EffectVariants are emitted here. Unknown passive tooltip
semantics remain outside this narrow bridge and therefore cannot be flattened into
static cooldown math.
"""

from pathlib import Path

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_progression import CharacterProgression
from services.extreme_skill_universe_service import ExtremeSkillUniverseService
from services.rotation_potion_cooldown_effect_variant_service import (
    POTION_COOLDOWN_REDUCTION_EFFECT,
)


class ExtremeSustainedDPSPotionCooldownPassiveGrantService:
    """Project explicit owned/ranked potion-cooldown passives into PassiveGrant rows."""

    def __init__(self, universe_service: ExtremeSkillUniverseService | object) -> None:
        self.universe_service = universe_service

    @classmethod
    def from_database(
        cls,
        database_path: str | Path,
    ) -> "ExtremeSustainedDPSPotionCooldownPassiveGrantService":
        return cls(ExtremeSkillUniverseService(database_path))

    @staticmethod
    def _key(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _cooldown_reduction_seconds(description: str) -> float | None:
        # No canonical player passive currently owns a reviewed static potion
        # cooldown reduction. Do not infer one from arbitrary prose.
        return None

    def resolve(
        self,
        player_build: object,
        progression: CharacterProgression,
    ) -> tuple[PassiveGrant, ...]:
        del player_build  # ownership is progression-scoped; retained for resolver protocol.
        if not progression.has_explicit_passive_progression:
            raise ValueError(
                "Extreme potion cooldown PassiveGrant derivation requires explicit passive ranks"
            )

        grants: list[PassiveGrant] = []
        for passive in self.universe_service.passives():
            name = str(getattr(passive, "name", "") or "").strip()
            line = str(getattr(passive, "skill_line", "") or "").strip()
            rank = progression.passive_rank(name)
            if rank is None or rank <= 0:
                continue
            description = str(getattr(passive, "description", "") or "")
            reduction = self._cooldown_reduction_seconds(description)
            normalized_description = self._key(description)
            if reduction is None and "potion" in normalized_description and "cooldown" in normalized_description:
                raise ValueError(
                    f"Owned passive {line}: {name} has unreviewed potion cooldown semantics"
                )
            if reduction is None:
                continue
            grants.append(
                PassiveGrant(
                    skill_line_id=line,
                    effect=EffectVariant(
                        name=POTION_COOLDOWN_REDUCTION_EFFECT,
                        layer=EffectLayer.PASSIVE,
                        source=name,
                        magnitude=float(reduction),
                    ),
                )
            )
        return tuple(grants)


__all__ = ["ExtremeSustainedDPSPotionCooldownPassiveGrantService"]
