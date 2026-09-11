from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_bar_transition import ExtremeRuntimeBarTransition
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)


class _LegacyGear:
    def __init__(self):
        self.calls = []

    def resolve_history(self, build, *, active_bar, attempts, snapshot_time_seconds):
        self.calls.append((build.BuildName, active_bar, attempts, snapshot_time_seconds))
        return SimpleNamespace(active_buffs=("Major Brutality",), unresolved=())


class _DualGear:
    def __init__(self):
        self.calls = []

    def resolve_history(
        self,
        activation,
        *,
        attempts,
        snapshot_time_seconds,
        snapshot_active_bar=None,
        bar_transitions=(),
        bar_transition_history_complete=False,
    ):
        self.calls.append(
            (
                activation,
                attempts,
                snapshot_time_seconds,
                snapshot_active_bar,
                bar_transitions,
                bar_transition_history_complete,
            )
        )
        return SimpleNamespace(active_buffs=("Major Courage",), unresolved=())


def _attempt(time_seconds: float = 1.0, sequence: int = 0):
    return RuntimeEffectEventAttempt(
        RuntimeEvent(
            time_seconds=time_seconds,
            trigger="overheal_self_or_ally",
            source="dual-bar snapshot integration",
            sequence=sequence,
        )
    )


def _bar_attempt(*, bar: str = "front", time_seconds: float = 1.0, sequence: int = 0):
    return ExtremeRuntimeBarEffectAttempt(
        attempt=_attempt(time_seconds=time_seconds, sequence=sequence),
        active_bar=bar,
    )


def test_dual_bar_activation_uses_bar_aware_runtime_path_without_legacy_double_projection():
    legacy = _LegacyGear()
    dual = _DualGear()
    activation = SimpleNamespace(evidence=("fixture",), unresolved=())
    tagged = _bar_attempt(bar="back")
    transition = ExtremeRuntimeBarTransition(1.5, 0, "back", "front")
    service = ExtremeRuntimeSnapshotCombatStateService(
        gear_runtime_buffs=legacy,
        dual_bar_gear_runtime=dual,
    )

    result = service.resolve(
        PlayerBuild(BuildName="Dual Bar Runtime"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            runtime_history=(tagged, transition),
            snapshot_time_seconds=2.0,
            bar_transition_history_complete=True,
        ),
        gear_activation=activation,
    )

    assert result.combat_state.active_buffs == ("Major Courage",)
    assert result.unresolved == ()
    assert dual.calls == [
        (activation, (tagged,), 2.0, "front", (transition,), True)
    ]
    assert legacy.calls == []


def test_dual_bar_activation_fails_closed_when_effect_attempt_lacks_bar_provenance():
    dual = _DualGear()
    service = ExtremeRuntimeSnapshotCombatStateService(dual_bar_gear_runtime=dual)

    result = service.resolve(
        PlayerBuild(BuildName="Missing Bar Provenance"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            runtime_history=(_attempt(),),
            snapshot_time_seconds=2.0,
        ),
        gear_activation=SimpleNamespace(evidence=("fixture",), unresolved=()),
    )

    assert result.combat_state.active_buffs == ()
    assert result.unresolved == (
        "Dual-bar gear runtime projection requires active-bar provenance for every effect attempt",
    )
    assert dual.calls == []


def test_legacy_gear_runtime_path_remains_available_without_dual_bar_activation_evidence():
    legacy = _LegacyGear()
    service = ExtremeRuntimeSnapshotCombatStateService(gear_runtime_buffs=legacy)
    attempt = _attempt()

    result = service.resolve(
        PlayerBuild(BuildName="Legacy Gear Runtime"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="back",
        snapshot=ExtremeRuntimeSnapshot(
            attempts=(attempt,),
            snapshot_time_seconds=2.0,
        ),
    )

    assert result.combat_state.active_buffs == ("Major Brutality",)
    assert result.unresolved == ()
    assert legacy.calls == [("Legacy Gear Runtime", "back", (attempt,), 2.0)]
