from services.extreme_power_record_runtime_requirement_service import (
    ExtremePowerRequirementOwner,
)
from services.extreme_spell_damage_record_service import ExtremeSpellDamageRecordService
from services.extreme_weapon_damage_record_service import ExtremeWeaponDamageRecordService


def _assert_contract(service, objective_key: str) -> None:
    requirements = service.runtime_requirements()
    witness = service.runtime_witness()

    assert len(requirements) == 9
    assert {row.objective_key for row in requirements} == {objective_key}
    assert sum(row.owner is ExtremePowerRequirementOwner.RUNTIME_HISTORY for row in requirements) == 3
    assert witness.objective_key == objective_key
    assert witness.closed is True
    assert witness.snapshot.runtime_history
    assert witness.snapshot.bar_transition_history_complete is True


def test_weapon_damage_record_exposes_machine_readable_runtime_contract() -> None:
    _assert_contract(ExtremeWeaponDamageRecordService(), "weapon_damage")


def test_spell_damage_record_exposes_machine_readable_runtime_contract() -> None:
    _assert_contract(ExtremeSpellDamageRecordService(), "spell_damage")
