from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateService,
)


class _ActiveBarAssessor:
    def active_bar_at(self, *args, **kwargs):
        del args, kwargs
        return "front"


class _BoundSnapshot:
    def snapshot_at(self, *args, **kwargs):
        del args, kwargs
        return object()


class _RuntimeBarProvenance:
    def bind(self, *args, **kwargs):
        del args, kwargs
        return SimpleNamespace(resolved=True, snapshot=_BoundSnapshot(), unresolved=())


class _RuntimeSnapshotState:
    def resolve(self, *args, **kwargs):
        del args
        base = kwargs["base_combat_state"]
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=True,
                active_buffs=tuple(base.active_buffs) + ("Minor Berserk",),
            ),
            unresolved=(),
        )


class _PotionState:
    def resolve(self, *args, **kwargs):
        del args
        base = kwargs["base_combat_state"]
        return SimpleNamespace(
            combat_state=CombatState(
                in_combat=base.in_combat,
                active_buffs=tuple(base.active_buffs) + ("Major Sorcery",),
            ),
            unresolved=(),
        )


def test_runtime_composition_layers_persistent_toggle_after_snapshot_and_potion_state() -> None:
    build = PlayerBuild(
        Name="Rylonia",
        BuildName="Corpsebuster DD",
        Role="DD",
        FrontBarSkills=["Magical Banner", "", "", "", "", ""],
        BackBarSkills=["Magical Banner", "", "", "", "", ""],
    )
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=2.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Magical Banner",
                bar="front",
            ),
        ),
    )
    service = RotationPlanRuntimeCombatStateService(
        active_bar_assessor=_ActiveBarAssessor(),  # type: ignore[arg-type]
        runtime_snapshot_state=_RuntimeSnapshotState(),  # type: ignore[arg-type]
        runtime_bar_provenance=_RuntimeBarProvenance(),  # type: ignore[arg-type]
        plan_potion_state=_PotionState(),  # type: ignore[arg-type]
    )
    source = SimpleNamespace(runtime_history=(object(),))

    before = service.resolve(
        build,
        progression=object(),  # type: ignore[arg-type]
        plan=plan,
        runtime_snapshot_source=source,  # type: ignore[arg-type]
        time_seconds=2.0,
        sequence=0,
    )
    after = service.resolve(
        build,
        progression=object(),  # type: ignore[arg-type]
        plan=plan,
        runtime_snapshot_source=source,  # type: ignore[arg-type]
        time_seconds=2.0,
        sequence=1,
    )

    assert before.resolved is True
    assert before.combat_state is not None
    assert before.combat_state.has_buff("Minor Berserk") is True
    assert before.combat_state.has_buff("Major Sorcery") is True
    assert before.combat_state.has_buff("Magical Banner") is False

    assert after.resolved is True
    assert after.combat_state is not None
    assert after.combat_state.has_buff("Minor Berserk") is True
    assert after.combat_state.has_buff("Major Sorcery") is True
    assert after.combat_state.has_buff("Magical Banner") is True
