from __future__ import annotations

"""Proof-backed sustained-DPS relevance classification for runtime EffectVariants."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.named_combat_buffs import (
    canonical_buff_name,
    effects_for_buff,
    is_component_layer_buff,
)
from minmax.stat_ids import StatId
from minmax.support_target_type import SupportTargetType


_DPS_STAT_IDS = frozenset(
    {
        StatId.WEAPON_DAMAGE,
        StatId.SPELL_DAMAGE,
        StatId.WEAPON_CRITICAL,
        StatId.SPELL_CRITICAL,
        StatId.CRITICAL_DAMAGE,
        StatId.MAX_MAGICKA,
        StatId.MAX_STAMINA,
        StatId.MAGICKA_RECOVERY,
        StatId.STAMINA_RECOVERY,
    }
)

_DPS_COMPONENT_BUFFS = frozenset(
    {
        "Minor Berserk",
        "Major Berserk",
        "Minor Slayer",
        "Major Slayer",
        "Minor Vulnerability",
        "Major Vulnerability",
        "Magical Banner",
    }
)

_PROVEN_NON_DPS_COMPONENT_BUFFS = frozenset(
    {
        "Minor Protection",
        "Major Protection",
        "Minor Aegis",
        "Major Aegis",
        "Minor Vitality",
        "Major Vitality",
        "Minor Defile",
        "Major Defile",
    }
)

_PROVEN_NON_DPS_IDENTITIES = frozenset(
    {
        "damage_shield",
    }
)


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeEffectRelevance:
    relevant: tuple[EffectVariant, ...]
    irrelevant: tuple[EffectVariant, ...]
    unresolved: tuple[str, ...]
    evidence: tuple[str, ...]


class ExtremeSustainedDPSRuntimeEffectRelevanceService:
    """Keep only runtime effects proven capable of changing modeled sustained DPS.

    This is intentionally conservative. An effect is removed only when canonical
    semantics prove that its current identity cannot change the DD objective.
    Unknown triggered identities remain unresolved rather than being assigned zero.
    """

    @classmethod
    def classify(
        cls,
        effects: tuple[EffectVariant, ...],
    ) -> ExtremeSustainedDPSRuntimeEffectRelevance:
        relevant: list[EffectVariant] = []
        irrelevant: list[EffectVariant] = []
        unresolved: list[str] = []

        for effect in effects:
            identity = str(effect.name or "").strip()
            key = identity.casefold()

            if key in _PROVEN_NON_DPS_IDENTITIES:
                irrelevant.append(effect)
                continue

            if key == "weapon_spell_damage":
                relevant.append(effect)
                continue

            buff = canonical_buff_name(identity.replace("_", " "))
            if buff is not None:
                if is_component_layer_buff(buff):
                    if buff in _DPS_COMPONENT_BUFFS:
                        if effect.target_type is SupportTargetType.ENEMY:
                            unresolved.append(
                                f"{effect.source} {buff} is DPS-relevant but enemy-target runtime projection is not modeled by Objective #32"
                            )
                        else:
                            relevant.append(effect)
                        continue
                    if buff in _PROVEN_NON_DPS_COMPONENT_BUFFS:
                        irrelevant.append(effect)
                        continue
                    unresolved.append(
                        f"{effect.source} {buff} has no reviewed sustained-DPS relevance disposition"
                    )
                    continue

                stat_effects = effects_for_buff(buff)
                if not stat_effects:
                    unresolved.append(
                        f"{effect.source} {buff} has no reviewed named-buff stat semantics for sustained-DPS relevance"
                    )
                    continue
                if any(row.stat in _DPS_STAT_IDS for row in stat_effects):
                    relevant.append(effect)
                else:
                    irrelevant.append(effect)
                continue

            unresolved.append(
                f"{effect.source} runtime effect {effect.name!r} has no reviewed sustained-DPS relevance disposition"
            )

        return ExtremeSustainedDPSRuntimeEffectRelevance(
            relevant=tuple(relevant),
            irrelevant=tuple(irrelevant),
            unresolved=tuple(dict.fromkeys(unresolved)),
            evidence=(
                f"Runtime effects relevance-reviewed: {len(effects)}",
                f"Runtime effects admitted to sustained-DPS state: {len(relevant)}",
                f"Runtime effects proven irrelevant to sustained DPS: {len(irrelevant)}",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeEffectRelevance",
    "ExtremeSustainedDPSRuntimeEffectRelevanceService",
]
