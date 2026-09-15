from services.extreme_power_record_runtime_requirement_service import (
    ExtremePowerRecordRuntimeRequirementService,
    ExtremePowerRequirementOwner,
)


def test_weapon_and_spell_power_records_have_parallel_requirement_shapes() -> None:
    weapon = ExtremePowerRecordRuntimeRequirementService.requirements_for("weapon_damage")
    spell = ExtremePowerRecordRuntimeRequirementService.requirements_for("spell_damage")

    assert len(weapon) == len(spell) == 9
    assert [row.owner for row in weapon] == [row.owner for row in spell]
    assert [row.requirement_id for row in weapon[:-2]] == [
        row.requirement_id for row in spell[:-2]
    ]


def test_runtime_snapshot_owned_requirements_are_explicit_event_families() -> None:
    for objective in ("weapon_damage", "spell_damage"):
        rows = ExtremePowerRecordRuntimeRequirementService.requirements_for(objective)
        runtime = tuple(row for row in rows if row.unified_runtime_snapshot_owned)

        assert {row.runtime_history_kind for row in runtime} == {
            "gear_proc",
            "potion_use",
            "external_group_buff",
        }
        assert all(row.owner is ExtremePowerRequirementOwner.RUNTIME_HISTORY for row in runtime)


def test_target_and_structural_facts_are_not_misowned_by_runtime_history() -> None:
    rows = ExtremePowerRecordRuntimeRequirementService.requirements_for("weapon_damage")
    by_id = {row.requirement_id: row for row in rows}

    assert by_id["target_execute_health"].owner is ExtremePowerRequirementOwner.TARGET_STATE
    assert by_id["target_off_balance_trigger"].owner is ExtremePowerRequirementOwner.TARGET_STATE
    assert by_id["same_build_higher_resource"].owner is ExtremePowerRequirementOwner.STRUCTURAL_STATE
    assert by_id["six_sorcerer_abilities_slotted"].owner is ExtremePowerRequirementOwner.ACTIVE_BAR
    assert by_id["font_of_power_active"].owner is ExtremePowerRequirementOwner.CLASS_RUNTIME
    assert by_id["calculated_defense_active"].owner is ExtremePowerRequirementOwner.CLASS_RUNTIME


def test_external_minor_power_is_runtime_history_with_provenance() -> None:
    weapon = {
        row.requirement_id: row
        for row in ExtremePowerRecordRuntimeRequirementService.requirements_for("weapon_damage")
    }
    spell = {
        row.requirement_id: row
        for row in ExtremePowerRecordRuntimeRequirementService.requirements_for("spell_damage")
    }

    assert weapon["external_minor_brutality"].external is True
    assert weapon["external_minor_brutality"].runtime_history_kind == "external_group_buff"
    assert spell["external_minor_sorcery"].external is True
    assert spell["external_minor_sorcery"].runtime_history_kind == "external_group_buff"


def test_unknown_power_record_objective_fails_closed() -> None:
    try:
        ExtremePowerRecordRuntimeRequirementService.requirements_for("bash_damage")
    except KeyError as exc:
        assert "unreviewed Extreme power-record objective" in str(exc)
    else:
        raise AssertionError("unknown power-record objective did not fail closed")
