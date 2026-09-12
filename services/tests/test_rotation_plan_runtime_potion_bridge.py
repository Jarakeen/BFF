from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.extreme_runtime_snapshot import ExtremeRuntimePotionUse, ExtremeRuntimeSnapshot
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateService,
)


class _RuntimeProjector:
    def resolve(self, build, **kwargs):
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=("Minor Berserk",),
                game_update=kwargs["base_combat_state"].game_update,
            ),
            unresolved=(),
        )


class _PlanPotionProjector:
    def __init__(self, *, unresolved=()) -> None:
        self.calls = []
        self.unresolved = tuple(unresolved)

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        if self.unresolved:
            return SimpleNamespace(combat_state=None, unresolved=self.unresolved)
        base = kwargs["base_combat_state"]
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=base.in_combat,
                active_buffs=(*base.active_buffs, "Major Brutality"),
                game_update=base.game_update,
            ),
            unresolved=(),
        )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=30.0,
        actions=(
            RotationAction(
                10.0,
                1,
                RotationActionKind.POTION,
                name="Alliance Battle Draught",
            ),
            RotationAction(10.0, 2, RotationActionKind.SKILL, name="Blastbones", bar="front"),
        ),
    )


def _source() -> ExtremeRuntimeSnapshot:
    return ExtremeRuntimeSnapshot(
        runtime_history=(ExtremeRuntimePotionUse(1.0, sequence=0),),
        snapshot_time_seconds=30.0,
    )


def test_shared_runtime_state_is_layered_through_exact_plan_potion_state() -> None:
    potion = _PlanPotionProjector()
    service = RotationPlanRuntimeCombatStateService(
        runtime_snapshot_state=_RuntimeProjector(),
        plan_potion_state=potion,
    )

    result = service.resolve(
        PlayerBuild(
            Name="Rylonia",
            BuildName="Corpsebuster DD",
            Role="DD",
            Potion="Alliance Battle Draught",
        ),
        progression=CharacterProgression(passive_ranks={"Medicinal Use": 3}),
        plan=_plan(),
        runtime_snapshot_source=_source(),
        time_seconds=10.0,
        sequence=2,
        base_combat_state=CombatState(game_update="U51"),
    )

    assert result.resolved is True
    assert result.combat_state is not None
    assert result.combat_state.active_buffs == ("Minor Berserk", "Major Brutality")
    assert len(potion.calls) == 1
    call = potion.calls[0][1]
    assert call["time_seconds"] == 10.0
    assert call["sequence"] == 2
    assert call["plan"] is not None
    assert call["base_combat_state"].active_buffs == ("Minor Berserk",)


def test_unresolved_plan_potion_state_fails_closed_at_runtime_boundary() -> None:
    potion = _PlanPotionProjector(unresolved=("scheduled potion runtime is unresolved",))
    service = RotationPlanRuntimeCombatStateService(
        runtime_snapshot_state=_RuntimeProjector(),
        plan_potion_state=potion,
    )

    result = service.resolve(
        PlayerBuild(
            Name="Rylonia",
            BuildName="Corpsebuster DD",
            Role="DD",
            Potion="Alliance Battle Draught",
        ),
        progression=CharacterProgression(passive_ranks={"Medicinal Use": 3}),
        plan=_plan(),
        runtime_snapshot_source=_source(),
        time_seconds=10.0,
        sequence=2,
    )

    assert result.resolved is False
    assert result.combat_state is None
    assert result.unresolved == ("scheduled potion runtime is unresolved",)
