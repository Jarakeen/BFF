from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)


def test_runtime_projection_preserves_non_runtime_base_combat_state() -> None:
    base = CombatState(
        in_combat=True,
        active_buffs=("Major Sorcery",),
        game_update="U51",
        is_emperor=True,
        in_home_campaign=True,
        emperor_home_keeps=4,
    )

    result = ExtremeRuntimeSnapshotCombatStateService().resolve(
        PlayerBuild(Name="Example", BuildName="Runtime", Role="Damage Dealer"),
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        snapshot=ExtremeRuntimeSnapshot(snapshot_time_seconds=5.0),
        base_combat_state=base,
    )

    assert result.unresolved == ()
    assert result.combat_state.in_combat is True
    assert result.combat_state.active_buffs == ("Major Sorcery",)
    assert str(result.combat_state.game_update.value) == "U51"
    assert result.combat_state.is_emperor is True
    assert result.combat_state.in_home_campaign is True
    assert result.combat_state.emperor_home_keeps == 4
