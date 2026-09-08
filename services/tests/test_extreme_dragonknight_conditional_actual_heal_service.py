from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_dragonknight_conditional_actual_heal_service import (
    ExtremeDragonknightConditionalActualHealService,
)


class _Optimizer:
    database_path = None

    def __init__(self):
        self.build_service = SimpleNamespace(
            canonical=SimpleNamespace(catalog_service=object())
        )
        self.context_factory = SimpleNamespace()


class _HealingEvents:
    pass


class _DragonknightMending:
    def __init__(self, *, buffs=("Major Mending",), unresolved=()):
        self.buffs = tuple(buffs)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, source_ability_name, major_mending_window_active):
        self.calls.append(
            (build.BuildName, source_ability_name, major_mending_window_active)
        )
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=self.buffs if not self.unresolved else (),
            ),
            unresolved=self.unresolved,
        )


class _HeavyState:
    def resolve(
        self,
        *,
        build,
        progression,
        active_bar,
        fully_charged_heavy_attack_completed,
    ):
        _ = build, progression, active_bar, fully_charged_heavy_attack_completed
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=("Major Mending",),
            ),
            unresolved=(),
        )


def _progression():
    return CharacterProgression(passive_ranks={"Essence Drain": 2})


def test_dragonknight_window_adds_major_mending():
    mending = _DragonknightMending()
    service = ExtremeDragonknightConditionalActualHealService(
        target_health_fraction=0.25,
        dragonknight_major_mending_window_active=True,
        dragonknight_major_mending_source_ability="Fragmented Shield",
        dragonknight_earthen_heart_mending=mending,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="DK Healer", EsoClass="Dragonknight"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.active_buffs == ("Major Mending",)
    assert unresolved == ()
    assert mending.calls == [("DK Healer", "Fragmented Shield", True)]


def test_duplicate_major_mending_sources_remain_one_named_buff():
    service = ExtremeDragonknightConditionalActualHealService(
        target_health_fraction=0.25,
        fully_charged_restoration_heavy_attack_completed=True,
        dragonknight_major_mending_window_active=True,
        dragonknight_major_mending_source_ability="Igneous Shield",
        dragonknight_earthen_heart_mending=_DragonknightMending(),
        restoration_heavy_state=_HeavyState(),
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Two Sources", EsoClass="Dragonknight"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.active_buffs == ("Major Mending",)
    assert unresolved == ()


def test_blocked_dragonknight_source_preserves_other_combat_state():
    service = ExtremeDragonknightConditionalActualHealService(
        target_health_fraction=0.25,
        fully_charged_restoration_heavy_attack_completed=True,
        dragonknight_major_mending_window_active=True,
        dragonknight_major_mending_source_ability="Mystery Shield",
        dragonknight_earthen_heart_mending=_DragonknightMending(
            buffs=(),
            unresolved=("Dragonknight Major Mending source unresolved",),
        ),
        restoration_heavy_state=_HeavyState(),
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Blocked DK", EsoClass="Dragonknight"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.active_buffs == ("Major Mending",)
    assert unresolved == ("Dragonknight Major Mending source unresolved",)
