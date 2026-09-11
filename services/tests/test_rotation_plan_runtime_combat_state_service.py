from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.extreme_runtime_snapshot import (
    ExtremeRuntimePotionUse,
    ExtremeRuntimeSnapshot,
)
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateService,
)


class _RuntimeProjector:
    def __init__(self, *, unresolved=()) -> None:
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        if self.unresolved:
            return SimpleNamespace(
                combat_state=CombatState(active_buffs=("should-not-escape",)),
                unresolved=self.unresolved,
            )
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=(f"bar:{kwargs['active_bar']}",),
                game_update=kwargs["base_combat_state"].game_update,
            ),
            unresolved=(),
        )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(
            RotationAction(10.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(10.0, 1, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(10.0, 2, RotationActionKind.SKILL, "Back Heal", "back"),
        ),
    )


def test_runtime_projection_uses_same_timestamp_plan_bar_and_history_sequence() -> None:
    projector = _RuntimeProjector()
    service = RotationPlanRuntimeCombatStateService(runtime_snapshot_state=projector)
    source = ExtremeRuntimeSnapshot(
        runtime_history=(
            ExtremeRuntimePotionUse(10.0, sequence=2),
            ExtremeRuntimePotionUse(10.0, sequence=0),
            ExtremeRuntimePotionUse(5.0, sequence=0),
        ),
        snapshot_time_seconds=20.0,
    )

    result = service.resolve(
        PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer"),
        progression=CharacterProgression(passive_ranks={}),
        plan=_plan(),
        runtime_snapshot_source=source,
        time_seconds=10.0,
        sequence=1,
        base_combat_state=CombatState(game_update="U51"),
    )

    assert result.resolved
    assert result.active_bar == "back"
    assert result.combat_state is not None
    assert result.combat_state.active_buffs == ("bar:back",)
    assert result.combat_state.game_update.value == "U51"
    assert len(projector.calls) == 1
    call = projector.calls[0][1]
    assert call["active_bar"] == "back"
    assert call["snapshot"].snapshot_time_seconds == 10.0
    assert [item.sequence for item in call["snapshot"].runtime_history] == [0, 0]


def test_runtime_projection_without_sequence_uses_state_after_all_same_timestamp_events() -> None:
    projector = _RuntimeProjector()
    service = RotationPlanRuntimeCombatStateService(runtime_snapshot_state=projector)
    source = ExtremeRuntimeSnapshot(
        runtime_history=(
            ExtremeRuntimePotionUse(10.0, sequence=2),
            ExtremeRuntimePotionUse(10.0, sequence=0),
        ),
        snapshot_time_seconds=20.0,
    )

    result = service.resolve(
        PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer"),
        progression=CharacterProgression(passive_ranks={}),
        plan=_plan(),
        runtime_snapshot_source=source,
        time_seconds=10.0,
    )

    assert result.resolved
    assert result.active_bar == "back"
    snapshot = projector.calls[0][1]["snapshot"]
    assert [item.sequence for item in snapshot.runtime_history] == [0, 2]


def test_legacy_one_snapshot_evidence_fails_closed_for_time_varying_projection() -> None:
    projector = _RuntimeProjector()
    service = RotationPlanRuntimeCombatStateService(runtime_snapshot_state=projector)

    result = service.resolve(
        PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer"),
        progression=CharacterProgression(passive_ranks={}),
        plan=_plan(),
        runtime_snapshot_source=ExtremeRuntimeSnapshot(
            snapshot_time_seconds=10.0,
            potion_elapsed_seconds=4.0,
        ),
        time_seconds=10.0,
    )

    assert not result.resolved
    assert result.combat_state is None
    assert result.active_bar == "back"
    assert projector.calls == []
    assert "legacy one-snapshot evidence" in result.unresolved[0]


def test_unresolved_shared_runtime_projection_blocks_combat_state() -> None:
    projector = _RuntimeProjector(unresolved=("gear proc target is unresolved",))
    service = RotationPlanRuntimeCombatStateService(runtime_snapshot_state=projector)

    result = service.resolve(
        PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer"),
        progression=CharacterProgression(passive_ranks={}),
        plan=_plan(),
        runtime_snapshot_source=ExtremeRuntimeSnapshot(
            runtime_history=(ExtremeRuntimePotionUse(5.0),),
            snapshot_time_seconds=10.0,
        ),
        time_seconds=10.0,
    )

    assert not result.resolved
    assert result.combat_state is None
    assert result.unresolved == ("gear proc target is unresolved",)
