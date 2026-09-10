from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_dragonknight_conditional_actual_heal_service import (
    ExtremeDragonknightConditionalActualHealService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult


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


class _ElderDragonState:
    def __init__(self, *, buffs=("Minor Brutality",), unresolved=()):
        self.buffs = tuple(buffs)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, progression, elder_dragon_window_active):
        self.calls.append(
            (build.BuildName, progression.passive_rank("Elder Dragon"), elder_dragon_window_active)
        )
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=self.buffs if not self.unresolved else (),
            ),
            unresolved=self.unresolved,
        )


class _DragonBloodHealing:
    def __init__(self, *, multiplier=1.0, unresolved=()):
        self.multiplier = float(multiplier)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, ability_name, caster_health_fraction):
        self.calls.append((build.BuildName, ability_name, caster_health_fraction))
        return SimpleNamespace(
            multiplier=self.multiplier,
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
    return CharacterProgression(
        passive_ranks={"Essence Drain": 2, "Elder Dragon": 2}
    )


def _event(skill_name="Dragon Blood", unresolved=()):
    return ExtremeHealingEventResult(
        entity_id="dragon_blood",
        normal_heal=1000.0,
        critical_heal=1700.0,
        critical_healing_bonus=0.20,
        critical_multiplier=1.70,
        heal_coefficient_numbers=(1,),
        crit_eligible_coefficient_numbers=(1,),
        noncrit_coefficient_numbers=(),
        tooltip_result=SimpleNamespace(skill=SimpleNamespace(name=skill_name)),
        unresolved=tuple(unresolved),
    )


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


def test_elder_dragon_window_adds_minor_brutality():
    elder = _ElderDragonState()
    service = ExtremeDragonknightConditionalActualHealService(
        target_health_fraction=0.25,
        elder_dragon_window_active=True,
        dragonknight_elder_dragon_state=elder,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Brutality DK", EsoClass="Dragonknight"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.active_buffs == ("Minor Brutality",)
    assert unresolved == ()
    assert elder.calls == [("Brutality DK", 2, True)]


def test_elder_dragon_and_major_mending_merge_without_overwrite():
    service = ExtremeDragonknightConditionalActualHealService(
        target_health_fraction=0.25,
        dragonknight_major_mending_window_active=True,
        dragonknight_major_mending_source_ability="Igneous Shield",
        elder_dragon_window_active=True,
        dragonknight_earthen_heart_mending=_DragonknightMending(),
        dragonknight_elder_dragon_state=_ElderDragonState(),
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Two DK Buffs", EsoClass="Dragonknight"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.active_buffs == ("Major Mending", "Minor Brutality")
    assert unresolved == ()


def test_elder_dragon_blocker_preserves_other_combat_state():
    service = ExtremeDragonknightConditionalActualHealService(
        target_health_fraction=0.25,
        fully_charged_restoration_heavy_attack_completed=True,
        elder_dragon_window_active=True,
        dragonknight_elder_dragon_state=_ElderDragonState(
            buffs=(),
            unresolved=("Elder Dragon legality unresolved",),
        ),
        restoration_heavy_state=_HeavyState(),
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )

    state, unresolved = service._restoration_combat_state(
        build=PlayerBuild(BuildName="Blocked Elder", EsoClass="Dragonknight"),
        progression=_progression(),
        active_bar="front",
    )

    assert state.active_buffs == ("Major Mending",)
    assert unresolved == ("Elder Dragon legality unresolved",)


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


def test_dragon_blood_missing_health_multiplier_scales_normal_and_critical_event():
    healing = _DragonBloodHealing(multiplier=1.375)
    service = ExtremeDragonknightConditionalActualHealService(
        target_health_fraction=0.25,
        caster_health_fraction=0.25,
        dragonknight_dragon_blood_healing=healing,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )
    build = PlayerBuild(BuildName="Blood DK", EsoClass="Dragonknight")

    result = service._dragon_blood_self_heal_event(build=build, event=_event())

    assert result.normal_heal == pytest.approx(1375.0)
    assert result.critical_heal == pytest.approx(2337.5)
    assert result.unresolved == ()
    assert healing.calls == [("Blood DK", "Dragon Blood", 0.25)]


def test_dragon_blood_unknown_caster_health_preserves_lower_bound_and_blocker():
    healing = _DragonBloodHealing(
        multiplier=1.0,
        unresolved=(
            "Dragon Blood missing-health scaling requires explicit caster Health fraction",
        ),
    )
    service = ExtremeDragonknightConditionalActualHealService(
        target_health_fraction=0.25,
        caster_health_fraction=None,
        dragonknight_dragon_blood_healing=healing,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )
    build = PlayerBuild(BuildName="Unknown Health DK", EsoClass="Dragonknight")

    result = service._dragon_blood_self_heal_event(build=build, event=_event())

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert result.unresolved == (
        "Dragon Blood missing-health scaling requires explicit caster Health fraction",
    )


def test_green_dragon_temporal_family_is_not_multiplied_by_dragon_blood_adapter():
    healing = _DragonBloodHealing(multiplier=1.375)
    service = ExtremeDragonknightConditionalActualHealService(
        target_health_fraction=0.25,
        caster_health_fraction=0.25,
        dragonknight_dragon_blood_healing=healing,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )
    event = _event(
        skill_name="Blood of the Green Dragon",
        unresolved=("temporal scope unresolved",),
    )

    result = service._dragon_blood_self_heal_event(
        build=PlayerBuild(BuildName="Green DK", EsoClass="Dragonknight"),
        event=event,
    )

    assert result is event
    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert healing.calls == []
