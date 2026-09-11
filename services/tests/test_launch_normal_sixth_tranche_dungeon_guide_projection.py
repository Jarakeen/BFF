from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _strategy(encounter_id: str, name: str):
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(encounter_id, name)
    assert projection.timeline
    return {row.mechanic: row for row in projection.strategy}


def test_vaults_of_madness_progression_bosses_have_reviewed_plans():
    ulguna = _strategy("ulguna_soul_reaver", "Ulguna Soul-Reaver")
    assert "Wave Attack" in ulguna
    assert "block" in ulguna["Wave Attack"].mitigation.casefold()
    assert "Levitation / Stifle" in ulguna
    assert "four feast orbs" in ulguna["Levitation / Stifle"].mitigation.casefold()

    grothdarr = _strategy("grothdarr", "Grothdarr")
    assert "Slam" in grothdarr
    assert "block" in grothdarr["Slam"].mitigation.casefold()
    assert "Lava Trails" in grothdarr
    assert "moving lava" in grothdarr["Lava Trails"].mitigation.casefold()

    iskra = _strategy("iskra_the_omen", "Iskra the Omen")
    assert "Breath" in iskra
    assert "sidestep" in iskra["Breath"].mitigation.casefold()
    assert "Leap" in iskra
    assert "furthest player" in iskra["Leap"].mitigation.casefold()

    architect = _strategy("mad_architect", "Mad Architect")
    assert "Undead Minions" in architect
    assert "kill" in architect["Undead Minions"].mitigation.casefold()
    assert "Undead Legion" in architect
    assert "move out" in architect["Undead Legion"].mitigation.casefold()
    assert "Obliterate" in architect
    assert "inside the protective dome" in architect["Obliterate"].mitigation.casefold()
