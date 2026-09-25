from __future__ import annotations

"""Resolve exact selected poison named effects from caller-owned dilution proof."""

from minmax.combat_effect_semantics import GameUpdate
from services.extreme_sustained_dps_weapon_poison_named_effect_consequence_service import (
    ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService,
)


class ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService:
    """Bridge explicit per-poison dilution selection into reviewed runtime effects."""

    def __init__(
        self,
        *,
        dilution_selection_resolver: object,
        game_update: GameUpdate | str = GameUpdate.U50,
    ) -> None:
        if dilution_selection_resolver is None:
            raise ValueError(
                "weapon-poison named-effect authority requires dilution-selection authority"
            )
        self.dilution_selection_resolver = dilution_selection_resolver
        self.game_update = game_update

    @staticmethod
    def _resolve_selection(
        resolver: object,
        *,
        poison_id: str,
        occurrence: object,
    ):
        if callable(resolver):
            return resolver(poison_id=poison_id, occurrence=occurrence)
        method = getattr(resolver, "resolve", None)
        if method is None:
            raise TypeError(
                "weapon-poison dilution-selection authority must be callable or expose resolve()"
            )
        return method(poison_id=poison_id, occurrence=occurrence)

    def resolve(self, *, poison_id: str, occurrence: object):
        selection = self._resolve_selection(
            self.dilution_selection_resolver,
            poison_id=poison_id,
            occurrence=occurrence,
        )
        if selection is None:
            raise ValueError(
                f"{str(poison_id or '').strip() or '(blank poison)'} has no explicit dilution-selection witness"
            )
        return ExtremeSustainedDPSWeaponPoisonNamedEffectConsequenceService(
            dilution_selection=selection,
            game_update=self.game_update,
        ).resolve(
            poison_id=poison_id,
            occurrence=occurrence,
        )


__all__ = [
    "ExtremeSustainedDPSWeaponPoisonNamedEffectAuthorityService",
]
