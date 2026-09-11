from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _strategy(encounter_id: str, name: str):
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(encounter_id, name)
    assert projection.timeline
    return {row.mechanic: row for row in projection.strategy}


def test_volenfell_progression_bosses_have_reviewed_plans():
    quintus = _strategy("quintus_verres", "Quintus Verres")
    assert "Fire Ground" in quintus
    assert "leave the large fire" in quintus["Fire Ground"].mitigation.casefold()
    assert "Gargoyle Slam" in quintus

    tremorscale = _strategy("tremorscale", "Tremorscale")
    assert "Tail Whip" in tremorscale
    assert "block or sidestep" in tremorscale["Tail Whip"].mitigation.casefold()
    assert "Burrow" in tremorscale

    council = _strategy("guardian_council", "Guardian Council")
    assert "Spark Barrage" in council
    assert "Soul Decapitation" in council
    assert "faced away" in council["Soul Decapitation"].mitigation.casefold()
    assert "Strength Whirlwind" in council
    assert "kite" in council["Strength Whirlwind"].mitigation.casefold()


def test_tempest_island_progression_bosses_have_reviewed_plans():
    valaran = _strategy("valaran_stormcaller", "Valaran Stormcaller")
    assert "Lightning Storm" in valaran
    assert "large lightning" in valaran["Lightning Storm"].mitigation.casefold()
    assert "Quick Shot" in valaran

    stormfist = _strategy("stormfist", "Stormfist")
    assert "Ground Fist" in stormfist
    assert "crushing-hand" in stormfist["Ground Fist"].mitigation.casefold()
    assert "Lightning Burst" in stormfist

    neidir = _strategy("stormreeve_neidir", "Stormreeve Neidir")
    assert "Sparking Strike" in neidir
    assert "leave the large aoe" in neidir["Sparking Strike"].mitigation.casefold()
    assert "Charge" in neidir
    assert "Gust of Winds" in neidir


def test_blackheart_haven_progression_bosses_have_reviewed_plans():
    atarus = _strategy("atarus", "Atarus")
    assert "Acid Puke" in atarus
    assert "poison cone" in atarus["Acid Puke"].mitigation.casefold()
    assert "Charge" in atarus

    roost = _strategy("roost_mother", "Roost Mother")
    assert "Flame Breath" in roost
    assert "frontal fire cone" in roost["Flame Breath"].mitigation.casefold()
    assert "Raining Fire" in roost
    assert "landing spots" in roost["Raining Fire"].mitigation.casefold()

    blackheart = _strategy("captain_blackheart", "Captain Blackheart")
    assert "Skeletons" in blackheart
    assert "pull ranged skeletons" in blackheart["Skeletons"].mitigation.casefold()
    assert "Spin" in blackheart
    assert "Skeleton Curse" in blackheart
    assert "transformed player" in blackheart["Skeleton Curse"].mitigation.casefold()
