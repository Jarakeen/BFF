from types import SimpleNamespace

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_power_record_runtime_snapshot_witness_service import (
    ExtremePowerRecordRuntimeSnapshotWitnessService,
)
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)


class _ArmorOfTruthRuntimeAdapter:
    def __init__(self) -> None:
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
        valid = any(
            tagged.attempt.event.trigger == "damage_off_balance_target"
            and tagged.attempt.event.source == "Armor of Truth reviewed 5pc trigger"
            and snapshot_time_seconds - tagged.attempt.event.time_seconds <= 10.0 + 1e-12
            for tagged in attempts
        )
        return SimpleNamespace(
            active_buffs=("Armor of Truth",) if valid else (),
            unresolved=() if valid else ("Armor of Truth trigger witness is not active",),
        )


class _PotionResolver:
    class _Event:
        unresolved = ()
        resolved = True
        duration_seconds = 47.6
        cooldown_seconds = 45.0
        buff_names = ("Major Brutality",)

    def __init__(self, buff_name: str) -> None:
        self.buff_name = buff_name

    def resolve(self, potion_name: str):
        event = self._Event()
        event.buff_names = (self.buff_name,)
        return event


class _PotionCadenceWindow:
    def __init__(self, active_buff_names):
        self.active_buff_names = active_buff_names


class _PotionCadence:
    def __init__(self, event, medicinal_use_rank):
        self.event = event

    def window(self, elapsed):
        return _PotionCadenceWindow(self.event.buff_names)


def _project(monkeypatch, objective_key: str, potion_name: str, major_buff: str):
    witness = ExtremePowerRecordRuntimeSnapshotWitnessService.build(objective_key)
    gear = _ArmorOfTruthRuntimeAdapter()
    monkeypatch.setattr(
        "services.extreme_runtime_snapshot_combat_state_service.PotionCadence",
        _PotionCadence,
    )
    service = ExtremeRuntimeSnapshotCombatStateService(
        dual_bar_gear_runtime=gear,
        potion_use_resolver=_PotionResolver(major_buff),
    )
    build = PlayerBuild(BuildName="Extreme Power Winner", Potion=potion_name)
    progression = CharacterProgression(passive_ranks={"Medicinal Use": 3})
    result = service.resolve(
        build,
        progression=progression,
        active_bar=witness.active_bar,
        snapshot=witness.snapshot,
        gear_activation=SimpleNamespace(evidence=("Armor of Truth 5pc",), unresolved=()),
    )
    return witness, result, gear


def test_weapon_damage_witness_projects_runtime_owned_conditions(monkeypatch) -> None:
    witness, result, gear = _project(
        monkeypatch,
        "weapon_damage",
        "Weapon Power potion",
        "Major Brutality",
    )

    assert witness.closed is True
    assert result.unresolved == ()
    assert set(result.combat_state.active_buffs) == {
        "Armor of Truth",
        "Major Brutality",
        "Minor Brutality",
    }
    assert len(gear.calls) == 1


def test_spell_damage_witness_projects_runtime_owned_conditions(monkeypatch) -> None:
    witness, result, gear = _project(
        monkeypatch,
        "spell_damage",
        "Spell Power potion",
        "Major Sorcery",
    )

    assert witness.closed is True
    assert result.unresolved == ()
    assert set(result.combat_state.active_buffs) == {
        "Armor of Truth",
        "Major Sorcery",
        "Minor Sorcery",
    }
    assert len(gear.calls) == 1


def test_witness_fails_closed_when_armor_of_truth_window_expired() -> None:
    witness = ExtremePowerRecordRuntimeSnapshotWitnessService.build(
        "weapon_damage",
        armor_of_truth_trigger_time_seconds=1.0,
        snapshot_time_seconds=15.0,
    )

    assert witness.closed is False
    assert any("10-second runtime window has expired" in row for row in witness.unresolved)


def test_witness_fails_closed_for_unsupported_objective() -> None:
    witness = ExtremePowerRecordRuntimeSnapshotWitnessService.build("critical_damage")

    assert witness.closed is False
    assert witness.expected_runtime_buffs == ()
    assert witness.unresolved == ("Unsupported power record objective: critical_damage",)
