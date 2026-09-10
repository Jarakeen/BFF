from __future__ import annotations

from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from minmax.stat_ids import StatId
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)


def test_proven_external_major_courage_reaches_canonical_spell_damage_math() -> None:
    build = PlayerBuild(BuildName="External Courage")
    progression = CharacterProgression(passive_ranks={})
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(
            ExternalGroupBuffApplication(
                source_actor_id="healer_2",
                recipient_actor_id="healer_1",
                buff_name="Major Courage",
                target_type=SupportTargetType.SELF_OR_ALLY,
                applied_at_seconds=10.0,
                duration_seconds=10.0,
                source_evidence="observed Spell Power Cure application",
            ),
        ),
        snapshot_time_seconds=12.0,
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2"),
    )

    projected = ExtremeRuntimeSnapshotCombatStateService().resolve(
        build,
        progression=progression,
        active_bar="front",
        snapshot=snapshot,
    )
    assert projected.unresolved == ()
    assert projected.combat_state.active_buffs == ("Major Courage",)

    baseline = BuildCalculationContextFactory().build(
        character_id="healer_1",
        build_id="baseline",
        build=build,
        progression=progression,
    )
    buffed = BuildCalculationContextFactory().build(
        character_id="healer_1",
        build_id="buffed",
        build=build,
        progression=progression,
        combat_state=projected.combat_state,
    )

    baseline_spell = baseline.core_state.derived[StatId.SPELL_DAMAGE].final_value
    buffed_spell = buffed.core_state.derived[StatId.SPELL_DAMAGE].final_value
    assert baseline_spell == 1000
    assert buffed_spell == 1430
    assert buffed_spell - baseline_spell == 430


def test_unproven_external_source_cannot_inflate_canonical_stats() -> None:
    build = PlayerBuild(BuildName="Blocked External Courage")
    progression = CharacterProgression(passive_ranks={})
    snapshot = ExtremeRuntimeSnapshot(
        runtime_history=(
            ExternalGroupBuffApplication(
                source_actor_id="not_on_roster",
                recipient_actor_id="healer_1",
                buff_name="Major Courage",
                target_type=SupportTargetType.SELF_OR_ALLY,
                applied_at_seconds=10.0,
                duration_seconds=10.0,
                source_evidence="claimed external application",
            ),
        ),
        snapshot_time_seconds=12.0,
        recipient_actor_id="healer_1",
        group_member_ids=("healer_1", "healer_2"),
    )

    projected = ExtremeRuntimeSnapshotCombatStateService().resolve(
        build,
        progression=progression,
        active_bar="front",
        snapshot=snapshot,
    )

    assert projected.combat_state.active_buffs == ()
    assert any("source is not a proven group member" in item for item in projected.unresolved)
