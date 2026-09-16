from models.build_model import PlayerBuild
from services.extreme_actual_heal_setup_action_legality_service import (
    ExtremeActualHealSetupActionWitness,
)
from services.extreme_actual_heal_setup_action_materialization_service import (
    ExtremeActualHealSetupActionMaterializationService,
)


def _witness(name: str = "Vigor") -> ExtremeActualHealSetupActionWitness:
    return ExtremeActualHealSetupActionWitness(
        capability="grants_resolve",
        skill_name=name,
        skill_line="Assault",
        ability_id=12345,
        evidence=f"{name}: route-legal Resolve witness",
    )


def test_setup_action_is_materialized_on_inactive_bar_without_touching_scored_heal_bar() -> None:
    build = PlayerBuild()
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = ["", "E", "F", "G", "H", "Back Ultimate"]

    result = ExtremeActualHealSetupActionMaterializationService.materialize(
        build,
        _witness(),
        active_bar="front",
    )

    assert result.materialized is True
    assert result.setup_bar == "back"
    assert result.slot_index == 0
    assert result.displaced_skill is None
    assert result.build.FrontBarSkills == build.FrontBarSkills
    assert result.build.BackBarSkills[0] == "Vigor"
    assert result.build.BackBarSkills[5] == "Back Ultimate"


def test_full_inactive_bar_replaces_one_ordinary_slot_and_records_displacement() -> None:
    build = PlayerBuild()
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = ["One", "Two", "Three", "Four", "Five", "Back Ultimate"]

    result = ExtremeActualHealSetupActionMaterializationService.materialize(
        build,
        _witness(),
        active_bar="front",
    )

    assert result.materialized is True
    assert result.slot_index == 4
    assert result.displaced_skill == "Five"
    assert result.build.FrontBarSkills == build.FrontBarSkills
    assert result.build.BackBarSkills[:5] == ["One", "Two", "Three", "Four", "Vigor"]
    assert result.build.BackBarSkills[5] == "Back Ultimate"


def test_full_inactive_bar_exposes_all_five_legal_replacement_variants() -> None:
    build = PlayerBuild()
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = ["One", "Two", "Three", "Four", "Five", "Back Ultimate"]

    variants = ExtremeActualHealSetupActionMaterializationService.variants(
        build,
        _witness(),
        active_bar="front",
    )

    assert [item.slot_index for item in variants] == [0, 1, 2, 3, 4]
    assert [item.displaced_skill for item in variants] == ["One", "Two", "Three", "Four", "Five"]
    assert all(item.build.FrontBarSkills == build.FrontBarSkills for item in variants)
    assert all(item.build.BackBarSkills[5] == "Back Ultimate" for item in variants)
    for item in variants:
        assert item.build.BackBarSkills[item.slot_index] == "Vigor"


def test_existing_setup_skill_is_reused_without_displacement() -> None:
    build = PlayerBuild()
    build.BackBarSkills = ["One", "Vigor", "Three", "Four", "Five", "Back Ultimate"]

    result = ExtremeActualHealSetupActionMaterializationService.materialize(
        build,
        _witness(),
        active_bar="front",
    )

    assert result.materialized is True
    assert result.slot_index == 1
    assert result.displaced_skill is None
    assert result.build.BackBarSkills == build.BackBarSkills


def test_unproven_setup_witness_fails_closed_without_mutating_build() -> None:
    build = PlayerBuild()
    build.FrontBarSkills = ["Scored Heal", "A", "B", "C", "D", "Front Ultimate"]
    build.BackBarSkills = ["One", "Two", "Three", "Four", "Five", "Back Ultimate"]
    witness = ExtremeActualHealSetupActionWitness(
        capability="grants_resolve",
        unresolved=("no legal witness",),
    )

    result = ExtremeActualHealSetupActionMaterializationService.materialize(
        build,
        witness,
        active_bar="front",
    )

    assert result.materialized is False
    assert result.build.to_dict() == build.to_dict()
    assert result.unresolved
