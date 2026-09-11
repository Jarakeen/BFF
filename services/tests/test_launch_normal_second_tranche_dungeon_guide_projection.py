from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _strategy(encounter_id: str, name: str):
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(encounter_id, name)
    assert projection.timeline
    return {row.mechanic: row for row in projection.strategy}


def test_darkshade_i_progression_bosses_have_reviewed_plans():
    llothan = _strategy("foreman_llothan", "Foreman Llothan")
    assert "Extracted Poison" in llothan
    assert "move out" in llothan["Extracted Poison"].mitigation.casefold()
    assert "Kwama Summon" in llothan

    hive = _strategy("the_hive_lord", "The Hive Lord")
    assert "Overhead Smash" in hive
    assert "block" in hive["Overhead Smash"].mitigation.casefold()
    assert "Ground Pound" in hive
    assert "bash" in hive["Ground Pound"].mitigation.casefold()

    sentinel = _strategy("sentinel_of_rkugamz", "Sentinel of Rkugamz")
    assert "Healing Spiders" in sentinel
    assert "healing spheres" in sentinel["Healing Spiders"].mitigation.casefold()
    assert "Cyclone" in sentinel
    assert "kite" in sentinel["Cyclone"].mitigation.casefold()


def test_elden_hollow_i_progression_bosses_have_reviewed_plans():
    akash = _strategy("akash_gra_mal", "Akash gra-Mal")
    assert "Cleave" in akash
    assert "facing away" in akash["Cleave"].mitigation.casefold()
    assert "Whirlwind" in akash

    chokethorn = _strategy("chokethorn", "Chokethorn")
    assert "Vine Pull" in chokethorn
    assert "stay reasonably close" in chokethorn["Vine Pull"].mitigation.casefold()
    assert "Burst" in chokethorn
    assert "expanding aoe" in chokethorn["Burst"].mitigation.casefold()

    oraneth = _strategy("canonreeve_oraneth", "Canonreeve Oraneth")
    assert "Poison Bolt" in oraneth
    assert "dodge roll" in oraneth["Poison Bolt"].mitigation.casefold()
    assert "Blast" in oraneth
    assert "Skeletons" in oraneth


def test_wayrest_sewers_i_progression_bosses_have_reviewed_plans():
    garron = _strategy("investigator_garron", "Investigator Garron")
    assert "Death's Embrace" in garron
    assert "never kite one through the group" in garron["Death's Embrace"].mitigation.casefold()
    assert "Restless Souls" in garron

    varaine = _strategy("varaine_pellingare", "Varaine Pellingare")
    assert "Frontal AOE" in varaine
    assert "sidestep" in varaine["Frontal AOE"].mitigation.casefold()
    assert "Jumping Spin" in varaine

    allene = _strategy("allene_pellingare_wayrest_sewers_i", "Allene Pellingare")
    assert "Power Attack" in allene
    assert "block" in allene["Power Attack"].mitigation.casefold()
    assert "Fiendish Hallucinations" in allene
    assert "kill them quickly" in allene["Fiendish Hallucinations"].mitigation.casefold()
