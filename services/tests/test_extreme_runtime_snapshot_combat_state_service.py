from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)


class _SkillHistory:
    def __init__(self):
        self.calls = []

    def active_triggered_named_buffs_history(
        self, build, *, active_bar, attempts, snapshot_time_seconds
    ):
        self.calls.append((build.BuildName, active_bar, attempts, snapshot_time_seconds))
        return ("Major Sorcery", "Major Sorcery")


class _GearHistory:
    def __init__(self, *, unresolved=()):
        self.calls = []
        self.unresolved = tuple(unresolved)

    def resolve_history(self, build, *, active_bar, attempts, snapshot_time_seconds):
        self.calls.append((build.BuildName, active_bar, attempts, snapshot_time_seconds))
        return SimpleNamespace(
            active_buffs=("Major Courage",), unresolved=self.unresolved
        )


class _PotionResolver:
    def resolve(self, selected_label):
        _ = selected_label
        return SimpleNamespace(
            resolved=True,
            unresolved=(),
            buff_grants=(SimpleNamespace(buff_name="Major Sorcery", duration=40.0),),
        )


def _attempt():
    return RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=1.0,
            trigger="critical_heal",
            source="snapshot state test",
        )
    )


def test_snapshot_state_projects_skill_gear_and_potion_into_one_combat_state():
    attempts = (_attempt(),)
    skill = _SkillHistory()
    gear = _GearHistory()
    service = ExtremeRuntimeSnapshotCombatStateService(
        skill_buff_candidates=skill,
        gear_runtime_buffs=gear,
        potion_use_resolver=_PotionResolver(),
    )

    result = service.resolve(
        PlayerBuild(BuildName="Shared Snapshot", Potion="Increase Spell Power"),
        progression=CharacterProgression(passive_ranks={"Medicinal Use": 3}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            attempts=attempts,
            snapshot_time_seconds=5.0,
            potion_elapsed_seconds=5.0,
        ),
        base_active_buffs=("Minor Mending", "Major Sorcery"),
    )

    assert result.unresolved == ()
    assert result.combat_state.in_combat
    assert result.combat_state.active_buffs == (
        "Minor Mending",
        "Major Sorcery",
        "Major Courage",
    )
    assert skill.calls[0][2:] == (attempts, 5.0)
    assert gear.calls[0][2:] == (attempts, 5.0)


def test_snapshot_state_preserves_gear_runtime_blockers():
    service = ExtremeRuntimeSnapshotCombatStateService(
        skill_buff_candidates=_SkillHistory(),
        gear_runtime_buffs=_GearHistory(unresolved=("proc stacking unresolved",)),
    )
    result = service.resolve(
        PlayerBuild(BuildName="Blocked Snapshot"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            attempts=(_attempt(),), snapshot_time_seconds=5.0
        ),
    )
    assert result.unresolved == ("proc stacking unresolved",)


def test_snapshot_state_requires_medicinal_use_proof_for_potion_window():
    service = ExtremeRuntimeSnapshotCombatStateService(
        potion_use_resolver=_PotionResolver()
    )
    result = service.resolve(
        PlayerBuild(BuildName="Potion Proof", Potion="Increase Spell Power"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            snapshot_time_seconds=5.0, potion_elapsed_seconds=5.0
        ),
    )
    assert result.unresolved == (
        "Medicinal Use rank is unresolved for explicit potion-use window",
    )


def test_snapshot_state_without_runtime_sources_preserves_base_state():
    service = ExtremeRuntimeSnapshotCombatStateService()
    result = service.resolve(
        PlayerBuild(BuildName="Static Snapshot"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(snapshot_time_seconds=0.0),
        base_active_buffs=("Major Sorcery", "Major Sorcery"),
    )
    assert not result.combat_state.in_combat
    assert result.combat_state.active_buffs == ("Major Sorcery",)
    assert result.unresolved == ()
