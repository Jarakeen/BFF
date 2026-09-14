from types import SimpleNamespace

import pytest

from minmax.character_build.character_class import CharacterClass
from services.extreme_recovery_class_route_frontier_service import (
    ExtremeRecoveryClassRouteFrontierService,
    _line_id,
)
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


def _passive(name: str, line: str, description: str):
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="Test",
        skill_line=line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=100,
        max_rank=2,
        max_rank_ability_id=200,
        description=description,
        domain=ExtremeSkillDomain.CLASS,
    )


def test_human_class_line_names_normalize_to_registry_ids():
    assert _line_id("Storm Calling") == "storm_calling"
    assert _line_id("Soldier of Apocrypha") == "soldier_of_apocrypha"
    assert _line_id("Winter's Embrace") == "winters_embrace"


def test_frontier_composes_static_line_and_slot_recovery(tmp_path, monkeypatch):
    service = ExtremeRecoveryClassRouteFrontierService(tmp_path / "missing.db")
    service.passives = (
        _passive("Capacitor", "Storm Calling", "Increases your Magicka Recovery by 141."),
        _passive(
            "Refreshing Shadows",
            "Shadow",
            "Increases your Health, Stamina, and Magicka Recovery by 15%.",
        ),
    )

    config = SimpleNamespace(
        base_class=CharacterClass.SORCERER,
        equipped_skill_lines=("storm_calling", "shadow", "soldier_of_apocrypha"),
        is_pure_class=False,
    )
    monkeypatch.setattr(
        "services.extreme_recovery_class_route_frontier_service.ExtremeClassConfigurationService.all_candidates",
        lambda: (config,),
    )
    monkeypatch.setattr(
        "services.extreme_recovery_class_route_frontier_service.ExtremeSubclassSlotAllocationService.best_allocation",
        lambda *args, **kwargs: SimpleNamespace(
            projected_delta=486.0,
            reviewed_sources=("Wellspring of the Abyss (6 Soldier of Apocrypha slots)",),
            slot_counts=(("soldier_of_apocrypha", 6),),
        ),
    )

    result = service.frontier("magicka_recovery", reference_value=1000.0)
    best = result.best_reviewed_candidate

    assert best is not None
    assert best.static_flat == pytest.approx(141.0)
    assert best.static_percent == pytest.approx(0.15)
    assert best.slot_projected_delta == pytest.approx(486.0)
    assert best.projected_delta == pytest.approx(777.0)
    assert result.route_denominator_closed


def test_flourish_is_not_counted_as_both_static_and_slot_recovery(tmp_path, monkeypatch):
    service = ExtremeRecoveryClassRouteFrontierService(tmp_path / "missing.db")
    service.passives = (
        _passive(
            "Flourish",
            "Animal Companions",
            "Increases your Magicka and Stamina Recovery by 20% while an Animal Companions ability is slotted.",
        ),
        _passive(
            "Erudition",
            "Curative Runeforms",
            "Increases your Magicka and Stamina Recovery by 18%.",
        ),
    )
    config = SimpleNamespace(
        base_class=CharacterClass.ARCANIST,
        equipped_skill_lines=("animal_companions", "curative_runeforms", "soldier_of_apocrypha"),
        is_pure_class=False,
    )
    monkeypatch.setattr(
        "services.extreme_recovery_class_route_frontier_service.ExtremeClassConfigurationService.all_candidates",
        lambda: (config,),
    )
    monkeypatch.setattr(
        "services.extreme_recovery_class_route_frontier_service.ExtremeSubclassSlotAllocationService.best_allocation",
        lambda *args, **kwargs: SimpleNamespace(
            projected_delta=605.0,
            reviewed_sources=(
                "Flourish (Animal Companions represented)",
                "Wellspring of the Abyss (5 Soldier of Apocrypha slots)",
            ),
            slot_counts=(
                ("animal_companions", 1),
                ("curative_runeforms", 0),
                ("soldier_of_apocrypha", 5),
            ),
        ),
    )

    result = service.frontier("magicka_recovery", reference_value=1000.0)
    best = result.best_reviewed_candidate

    assert best is not None
    assert best.static_percent == pytest.approx(0.18)
    assert best.slot_projected_delta == pytest.approx(605.0)
    assert best.projected_delta == pytest.approx(785.0)
    assert sum("Flourish" in source for source in best.reviewed_sources) == 1


def test_contextual_recovery_stays_runtime_obligation(tmp_path, monkeypatch):
    service = ExtremeRecoveryClassRouteFrontierService(tmp_path / "missing.db")
    service.passives = (
        _passive(
            "Undead Confederate",
            "Living Death",
            "While you have a Spirit Mender active, your Health, Magicka, and Stamina Recovery is increased by 155.",
        ),
    )
    config = SimpleNamespace(
        base_class=CharacterClass.NECROMANCER,
        equipped_skill_lines=("living_death", "shadow", "storm_calling"),
        is_pure_class=False,
    )
    monkeypatch.setattr(
        "services.extreme_recovery_class_route_frontier_service.ExtremeClassConfigurationService.all_candidates",
        lambda: (config,),
    )
    monkeypatch.setattr(
        "services.extreme_recovery_class_route_frontier_service.ExtremeSubclassSlotAllocationService.best_allocation",
        lambda *args, **kwargs: None,
    )

    result = service.frontier("magicka_recovery", reference_value=1000.0)

    assert not result.route_denominator_closed
    assert result.unresolved_runtime_obligations == ("Living Death: Undead Confederate",)
    assert result.best_reviewed_candidate.projected_delta == 0.0
