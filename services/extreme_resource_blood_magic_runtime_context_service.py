from __future__ import annotations

"""Canonical context bridge for the reviewed Blood Magic resource window.

The bridge performs the required two-pass calculation. It first builds the normal
pre-window context, delegates the higher-resource decision to
``ExtremeSorcererBloodMagicService``, then rebuilds through canonical ``CombatState``
with the named Blood Magic resource buff only when that window benefits the
requested objective. No resource percentage math is duplicated here.
"""

from dataclasses import replace

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.context_factory import BuildCalculationContextFactory
from models.build_model import PlayerBuild
from services.extreme_sorcerer_blood_magic_service import ExtremeSorcererBloodMagicService


class ExtremeResourceBloodMagicRuntimeContextService:
    """Apply one proven full-Health Blood Magic trigger to a canonical context."""

    SUPPORTED_OBJECTIVES = ("max_magicka", "max_stamina")

    def __init__(
        self,
        database_path=None,
        *,
        blood_magic_service: ExtremeSorcererBloodMagicService | None = None,
    ) -> None:
        self.blood_magic_service = blood_magic_service or ExtremeSorcererBloodMagicService(
            database_path
        )

    @staticmethod
    def _build(
        *,
        factory: BuildCalculationContextFactory,
        build: PlayerBuild,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        active_bar: str,
        combat_state: CombatState | None,
    ):
        kwargs = dict(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=progression,
            active_bar=active_bar,
        )
        if combat_state is not None:
            kwargs["combat_state"] = combat_state
        return factory.build(**kwargs)

    def resolve(
        self,
        *,
        factory: BuildCalculationContextFactory,
        build: PlayerBuild,
        progression: CharacterProgression,
        objective_key: str,
        trigger_ability_name: str,
        character_id: str,
        build_id: str,
        active_bar: str = "front",
        combat_state: CombatState | None = None,
    ):
        key = str(objective_key or "").strip().casefold()
        if key not in self.SUPPORTED_OBJECTIVES:
            raise KeyError(f"unsupported Blood Magic Extreme resource objective: {objective_key!r}")

        base_context = self._build(
            factory=factory,
            build=build,
            progression=progression,
            character_id=character_id,
            build_id=build_id,
            active_bar=active_bar,
            combat_state=combat_state,
        )
        resolved = self.blood_magic_service.resolve(
            build=build,
            progression=progression,
            context=base_context,
            trigger_ability_name=trigger_ability_name,
            trigger_ability_has_cost=True,
            caster_health_fraction=1.0,
        )
        if resolved.unresolved:
            return base_context, resolved.unresolved, resolved.resource_stat
        if resolved.branch != "resource_window" or resolved.resource_stat != key:
            return base_context, (), resolved.resource_stat

        buff_name = (
            "Blood Magic: Max Magicka"
            if key == "max_magicka"
            else "Blood Magic: Max Stamina"
        )
        if combat_state is None:
            window_state = CombatState(
                in_combat=True,
                active_buffs=(buff_name,),
            )
        else:
            window_state = replace(
                combat_state,
                in_combat=True,
                active_buffs=(*combat_state.active_buffs, buff_name),
            )
        context = self._build(
            factory=factory,
            build=build,
            progression=progression,
            character_id=character_id,
            build_id=f"{build_id}:blood-magic:{key}",
            active_bar=active_bar,
            combat_state=window_state,
        )
        return context, (), resolved.resource_stat
