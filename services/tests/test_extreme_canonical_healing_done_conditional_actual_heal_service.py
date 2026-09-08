from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_canonical_healing_done_conditional_actual_heal_service import (
    ExtremeCanonicalHealingDoneConditionalActualHealService,
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


class _CurativeCurse:
    def __init__(self, multiplier=1.12, unresolved=()):
        self.multiplier = multiplier
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, progression, has_negative_effect):
        self.calls.append((build.BuildName, progression, has_negative_effect))
        return SimpleNamespace(
            multiplier=self.multiplier,
            unresolved=self.unresolved,
        )


class _HealingTides:
    def __init__(self, multiplier=1.08, unresolved=()):
        self.multiplier = multiplier
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, progression, active_crux):
        self.calls.append((build.BuildName, progression, active_crux))
        return SimpleNamespace(
            multiplier=self.multiplier,
            unresolved=self.unresolved,
        )


def _service(*, curse=None, tides=None, negative=True, crux=2):
    return ExtremeCanonicalHealingDoneConditionalActualHealService(
        target_health_fraction=0.25,
        healer_has_negative_effect=negative,
        active_crux=crux,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
        necromancer_living_death_healing=curse,
        arcanist_curative_runeforms_healing=tides,
    )


def test_curative_curse_and_healing_tides_add_before_event_evaluation():
    curse = _CurativeCurse(multiplier=1.12)
    tides = _HealingTides(multiplier=1.08)
    service = _service(curse=curse, tides=tides)
    progression = CharacterProgression(passive_ranks={})
    build = PlayerBuild(BuildName="Conditional Stack")

    bonus, sources, unresolved = service._conditional_healing_done_inputs(
        build=build,
        progression=progression,
        entity_id="combat_prayer",
    )

    assert bonus == pytest.approx(0.20)
    assert sources == (
        "Necromancer: Curative Curse",
        "Arcanist: Healing Tides",
    )
    assert unresolved == ()
    assert curse.calls == [("Conditional Stack", progression, True)]
    assert tides.calls == [("Conditional Stack", progression, 2)]


def test_crux_consuming_heal_blocks_healing_tides_without_losing_other_healing_done():
    curse = _CurativeCurse(multiplier=1.12)
    tides = _HealingTides(multiplier=1.12)
    service = _service(curse=curse, tides=tides, crux=3)

    bonus, sources, unresolved = service._conditional_healing_done_inputs(
        build=PlayerBuild(BuildName="Cascading"),
        progression=CharacterProgression(passive_ranks={}),
        entity_id="cascading_fortune",
    )

    assert bonus == pytest.approx(0.12)
    assert sources == ("Necromancer: Curative Curse",)
    assert any("Healing Tides timing is unresolved" in message for message in unresolved)
    assert tides.calls == []


def test_unrequested_conditional_healing_done_remains_neutral():
    curse = _CurativeCurse(multiplier=1.12)
    tides = _HealingTides(multiplier=1.12)
    service = _service(curse=curse, tides=tides, negative=None, crux=None)

    bonus, sources, unresolved = service._conditional_healing_done_inputs(
        build=PlayerBuild(BuildName="Standing"),
        progression=CharacterProgression(passive_ranks={}),
        entity_id="combat_prayer",
    )

    assert bonus == 0.0
    assert sources == ()
    assert unresolved == ()
    assert curse.calls == []
    assert tides.calls == []


def test_unresolved_conditional_sources_preserve_numeric_lower_bound_blockers():
    curse = _CurativeCurse(
        multiplier=1.0,
        unresolved=("Curative Curse passive rank is not recorded",),
    )
    tides = _HealingTides(
        multiplier=1.0,
        unresolved=("Healing Tides passive rank is not recorded",),
    )
    service = _service(curse=curse, tides=tides)

    bonus, sources, unresolved = service._conditional_healing_done_inputs(
        build=PlayerBuild(BuildName="Unknowns"),
        progression=CharacterProgression(passive_ranks=None),
        entity_id="combat_prayer",
    )

    assert bonus == 0.0
    assert sources == ()
    assert unresolved == (
        "Curative Curse passive rank is not recorded",
        "Healing Tides passive rank is not recorded",
    )
