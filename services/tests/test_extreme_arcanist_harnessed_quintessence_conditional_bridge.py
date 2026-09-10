from dataclasses import dataclass
from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.extreme_arcanist_conditional_actual_heal_service import (
    ExtremeArcanistConditionalActualHealService,
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


class _Harnessed:
    def __init__(self, *, bonus=284.0, unresolved=()):
        self.bonus = float(bonus)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, progression, harnessed_quintessence_active):
        self.calls.append(
            (build.BuildName, progression, harnessed_quintessence_active)
        )
        return SimpleNamespace(
            weapon_spell_damage_bonus=self.bonus,
            duration_seconds=10.0 if self.bonus else 0.0,
            unresolved=self.unresolved,
        )


class _PowerContext:
    def __init__(self):
        self.calls = []

    def apply(self, context, *, weapon_spell_damage_bonus):
        self.calls.append((context, weapon_spell_damage_bonus))
        return _Context(power=context.power + float(weapon_spell_damage_bonus))


@dataclass(frozen=True)
class _Context:
    power: float



def _service(*, harnessed, power_context, active):
    return ExtremeArcanistConditionalActualHealService(
        target_health_fraction=0.25,
        harnessed_quintessence_active=active,
        arcanist_harnessed_quintessence=harnessed,
        arcanist_harnessed_quintessence_context=power_context,
        optimizer=_Optimizer(),
        healing_events=_HealingEvents(),
    )


def test_active_harnessed_window_adjusts_context_before_heal_layer():
    harnessed = _Harnessed(bonus=284.0)
    power_context = _PowerContext()
    service = _service(
        harnessed=harnessed,
        power_context=power_context,
        active=True,
    )
    context = _Context(power=2000.0)
    progression = object()

    updated, unresolved = service._harnessed_quintessence_context(
        build=PlayerBuild(BuildName="Harnessed Arc", EsoClass="Arcanist"),
        progression=progression,
        context=context,
    )

    assert updated.power == 2284.0
    assert unresolved == ()
    assert harnessed.calls == [("Harnessed Arc", progression, True)]
    assert power_context.calls == [(context, 284.0)]


def test_inactive_harnessed_window_leaves_context_unchanged():
    harnessed = _Harnessed(bonus=0.0)
    power_context = _PowerContext()
    service = _service(
        harnessed=harnessed,
        power_context=power_context,
        active=False,
    )
    context = _Context(power=2000.0)

    updated, unresolved = service._harnessed_quintessence_context(
        build=PlayerBuild(BuildName="Inactive Arc", EsoClass="Arcanist"),
        progression=object(),
        context=context,
    )

    assert updated is context
    assert unresolved == ()
    assert power_context.calls == []


def test_harnessed_legality_blocker_survives_without_power_mutation():
    blocker = "Harnessed Quintessence legality unresolved"
    harnessed = _Harnessed(bonus=0.0, unresolved=(blocker,))
    power_context = _PowerContext()
    service = _service(
        harnessed=harnessed,
        power_context=power_context,
        active=True,
    )
    context = _Context(power=2000.0)

    updated, unresolved = service._harnessed_quintessence_context(
        build=PlayerBuild(BuildName="Blocked Arc", EsoClass="Arcanist"),
        progression=object(),
        context=context,
    )

    assert updated is context
    assert unresolved == (blocker,)
    assert power_context.calls == []
