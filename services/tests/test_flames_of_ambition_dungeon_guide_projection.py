from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _markers(projection):
    return {row.marker for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_kinras_projection_has_salamander_control_and_hardmode_tank_pressure():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "kinras_ironeye", "Kinras Ironeye"
    )

    assert "Main Phase" in _labels(projection)
    strategy = _strategy(projection)
    assert "Blazing Salamanders" in strategy
    assert "before" in strategy["Blazing Salamanders"].mitigation.casefold()
    assert "Volcanic Smash" in strategy
    assert "tank" in strategy["Volcanic Smash"].mitigation.casefold()


def test_geminus_projection_preserves_tremor_and_trap_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "captain_geminus", "Captain Geminus"
    )

    assert "Mobile Main Phase" in _labels(projection)
    strategy = _strategy(projection)
    assert "Seismic Tremor" in strategy
    assert "move" in strategy["Seismic Tremor"].mitigation.casefold()
    assert "Incapacitating Trap" in strategy


def test_encratis_projection_has_inner_library_firestorm_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "pyroturge_encratis", "Pyroturge Encratis"
    )

    assert {"Outer Library", "Inner Library"} <= _labels(projection)
    assert "~65% to death" in _markers(projection)
    strategy = _strategy(projection)
    assert "Fire Storm" in strategy
    assert "safe eye" in strategy["Fire Storm"].mitigation.casefold()
    assert "Fire Behemoth" in strategy


def test_oxblood_projection_has_glob_management():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "oxblood_the_depraved", "Oxblood the Depraved"
    )

    assert "Main Phase / Glob Cycles" in _labels(projection)
    strategy = _strategy(projection)
    assert "Gore and Bile Globs" in strategy
    assert "bile" in strategy["Gore and Bile Globs"].mitigation.casefold()
    assert "Noxious Release" in strategy


def test_viccia_projection_has_trap_and_interrupt_plan():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "taskmaster_viccia", "Taskmaster Viccia"
    )

    assert "Trap-Control Main Phase" in _labels(projection)
    strategy = _strategy(projection)
    assert "Electric Traps" in strategy
    assert "avoid" in strategy["Electric Traps"].mitigation.casefold()
    assert "Execution Beam" in strategy
    assert "interrupt" in strategy["Execution Beam"].mitigation.casefold()


def test_molten_guardian_and_zaudrus_projection_cover_cauldron_endgame():
    guardian = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "molten_guardian", "Molten Guardian"
    )
    guardian_strategy = _strategy(guardian)
    assert "Magmatic Eruption" in guardian_strategy
    assert "Molten Fiends" in guardian_strategy

    zaudrus = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "baron_zaudrus", "Baron Zaudrus"
    )
    assert {"Main Phase", "Hard Mode Ash Vent Execute"} <= _labels(zaudrus)
    assert "~35% to death (Hard Mode)" in _markers(zaudrus)
    strategy = _strategy(zaudrus)
    assert "Ash Vent" in strategy
    assert "move" in strategy["Ash Vent"].mitigation.casefold()
    assert "Molten Pillars" in strategy
