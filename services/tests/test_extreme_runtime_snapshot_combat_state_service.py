from __future__ import annotations

from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.extreme_runtime_snapshot import (
    ExtremeRuntimePotionUse,
    ExtremeRuntimeSnapshot,
)
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


def _attempt(*, time_seconds=1.0, sequence=0):
    return RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=time_seconds,
            trigger="critical_heal",
            source="snapshot state test",
            sequence=sequence,
        )
    )


def _external_buff(**overrides):
    values = {
        "source_actor_id": "healer_2",
        "recipient_actor_id": "healer_1",
        "buff_name": "Major Courage",
        "target_type": SupportTargetType.SELF_OR_ALLY,
        "applied_at_seconds": 2.0,
        "duration_seconds": 8.0,
        "source_evidence": "observed support application",
    }
    values.update(overrides)
    return ExternalGroupBuffApplication(**values)


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


def test_snapshot_state_projects_unified_history_into_existing_consumers():
    late_attempt = _attempt(time_seconds=4.0, sequence=2)
    early_attempt = _attempt(time_seconds=1.0, sequence=3)
    expected_attempts = (early_attempt, late_attempt)
    skill = _SkillHistory()
    gear = _GearHistory()
    service = ExtremeRuntimeSnapshotCombatStateService(
        skill_buff_candidates=skill,
        gear_runtime_buffs=gear,
        potion_use_resolver=_PotionResolver(),
    )

    result = service.resolve(
        PlayerBuild(BuildName="Unified Snapshot", Potion="Increase Spell Power"),
        progression=CharacterProgression(passive_ranks={"Medicinal Use": 3}),
        active_bar="back",
        snapshot=ExtremeRuntimeSnapshot(
            runtime_history=(
                late_attempt,
                ExtremeRuntimePotionUse(time_seconds=2.0, sequence=1),
                early_attempt,
            ),
            snapshot_time_seconds=5.0,
        ),
    )

    assert result.unresolved == ()
    assert result.combat_state.in_combat
    assert result.combat_state.active_buffs == (
        "Major Sorcery",
        "Major Courage",
    )
    assert skill.calls == [("Unified Snapshot", "back", expected_attempts, 5.0)]
    assert gear.calls == [("Unified Snapshot", "back", expected_attempts, 5.0)]


def test_snapshot_state_projects_external_group_buff_only_with_roster_and_recipient_proof():
    service = ExtremeRuntimeSnapshotCombatStateService()
    result = service.resolve(
        PlayerBuild(BuildName="External Buff Snapshot"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            runtime_history=(_external_buff(),),
            snapshot_time_seconds=5.0,
            recipient_actor_id="healer_1",
            group_member_ids=("healer_1", "healer_2"),
        ),
    )

    assert result.combat_state.active_buffs == ("Major Courage",)
    assert result.unresolved == ()


def test_snapshot_state_external_group_buff_fails_closed_without_identity_proof():
    service = ExtremeRuntimeSnapshotCombatStateService()
    application = _external_buff()

    missing_recipient = service.resolve(
        PlayerBuild(BuildName="Missing Recipient"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            runtime_history=(application,),
            snapshot_time_seconds=5.0,
            group_member_ids=("healer_1", "healer_2"),
        ),
    )
    missing_group = service.resolve(
        PlayerBuild(BuildName="Missing Group"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            runtime_history=(application,),
            snapshot_time_seconds=5.0,
            recipient_actor_id="healer_1",
        ),
    )

    assert missing_recipient.combat_state.active_buffs == ()
    assert missing_recipient.unresolved == (
        "External group buff applications require a proven recipient actor id",
    )
    assert missing_group.combat_state.active_buffs == ()
    assert missing_group.unresolved == (
        "External group buff applications require proven group membership",
    )


def test_snapshot_state_external_group_buff_preserves_provenance_blocker():
    service = ExtremeRuntimeSnapshotCombatStateService()
    result = service.resolve(
        PlayerBuild(BuildName="Unknown Source"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            runtime_history=(_external_buff(source_actor_id="outsider"),),
            snapshot_time_seconds=5.0,
            recipient_actor_id="healer_1",
            group_member_ids=("healer_1", "healer_2"),
        ),
    )

    assert result.combat_state.active_buffs == ()
    assert any("source is not a proven group member" in item for item in result.unresolved)


def test_snapshot_state_future_potion_use_does_not_activate_buff():
    service = ExtremeRuntimeSnapshotCombatStateService(
        potion_use_resolver=_PotionResolver()
    )
    result = service.resolve(
        PlayerBuild(BuildName="Future Potion", Potion="Increase Spell Power"),
        progression=CharacterProgression(passive_ranks={"Medicinal Use": 3}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(
            runtime_history=(ExtremeRuntimePotionUse(time_seconds=6.0),),
            snapshot_time_seconds=5.0,
        ),
    )

    assert result.combat_state.active_buffs == ()
    assert result.unresolved == ()


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
