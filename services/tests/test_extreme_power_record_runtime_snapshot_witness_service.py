from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from models.build_model import PlayerBuild
from services.extreme_dual_bar_gear_runtime_legality_service import (
    ExtremeDualBarGearRuntimeLegalityService,
)
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidence,
    ExtremeDualBarSetActivationEvidenceCatalog,
    ExtremeDualBarSetActivationScope,
)
from services.extreme_power_record_runtime_snapshot_witness_service import (
    ExtremePowerRecordRuntimeSnapshotWitnessService,
)
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)


DATABASE = Path(__file__).resolve().parents[2] / "data" / "eso.db"


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


def _armor_of_truth_activation(repository: GearSetRepository) -> ExtremeDualBarSetActivationEvidenceCatalog:
    gear_set = repository.get_set("Armor of Truth")
    assert gear_set is not None
    return ExtremeDualBarSetActivationEvidenceCatalog(
        evidence=(
            ExtremeDualBarSetActivationEvidence(
                set_id=int(gear_set.id),
                set_name=str(gear_set.name),
                category=str(gear_set.category or ""),
                front_count=5,
                back_count=5,
                front_active_breakpoints=(2, 3, 4, 5),
                back_active_breakpoints=(2, 3, 4, 5),
                activation_scope=ExtremeDualBarSetActivationScope.BOTH,
                weapon_only_two_piece=False,
            ),
        ),
    )


def _project(monkeypatch, objective_key: str, potion_name: str, major_buff: str):
    witness = ExtremePowerRecordRuntimeSnapshotWitnessService.build(objective_key)
    repository = GearSetRepository(DATABASE)
    gear = ExtremeDualBarGearRuntimeLegalityService(
        resolver=GearSetEffectVariantResolver(repository)
    )
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
        gear_activation=_armor_of_truth_activation(repository),
    )
    return witness, result


def _assert_armor_of_truth_effect(result) -> None:
    matches = tuple(
        effect
        for effect in result.active_effects
        if effect.name == "weapon_spell_damage"
        and abs(float(effect.magnitude or 0.0) - 460.0) <= 1e-12
        and effect.trigger == "damage_off_balance_target"
    )
    assert len(matches) == 1


def test_weapon_damage_witness_projects_runtime_owned_conditions(monkeypatch) -> None:
    witness, result = _project(
        monkeypatch,
        "weapon_damage",
        "Weapon Power potion",
        "Major Brutality",
    )

    assert witness.closed is True
    assert result.unresolved == ()
    assert set(result.combat_state.active_buffs) == {
        "Major Brutality",
        "Minor Brutality",
    }
    _assert_armor_of_truth_effect(result)


def test_spell_damage_witness_projects_runtime_owned_conditions(monkeypatch) -> None:
    witness, result = _project(
        monkeypatch,
        "spell_damage",
        "Spell Power potion",
        "Major Sorcery",
    )

    assert witness.closed is True
    assert result.unresolved == ()
    assert set(result.combat_state.active_buffs) == {
        "Major Sorcery",
        "Minor Sorcery",
    }
    _assert_armor_of_truth_effect(result)


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
