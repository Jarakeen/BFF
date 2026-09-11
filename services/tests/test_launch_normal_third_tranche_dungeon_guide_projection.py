from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _strategy(encounter_id: str, name: str):
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(encounter_id, name)
    assert projection.timeline
    return {row.mechanic: row for row in projection.strategy}


def test_arx_corinium_progression_bosses_have_reviewed_plans():
    ganakton = _strategy("ganakton_the_tempest", "Ganakton the Tempest")
    assert "Shocking Breath" in ganakton
    assert "faced away" in ganakton["Shocking Breath"].mitigation.casefold()
    assert "Lightning Spit" in ganakton

    sliklenia = _strategy("sliklenia_the_songstress", "Sliklenia the Songstress")
    assert "Cacophony" in sliklenia
    assert "protective bubble" in sliklenia["Cacophony"].mitigation.casefold()
    assert "Venomous Bite" in sliklenia
    assert "block" in sliklenia["Venomous Bite"].mitigation.casefold()

    sellistrix = _strategy("sellistrix_the_lamia_queen", "Sellistrix the Lamia Queen")
    assert "Piercing Shriek" in sellistrix
    assert "block" in sellistrix["Piercing Shriek"].mitigation.casefold()
    assert "Bolt Discharge" in sellistrix
    assert "water" in sellistrix["Bolt Discharge"].mitigation.casefold()


def test_city_of_ash_i_progression_bosses_have_reviewed_plans():
    infernal = _strategy("infernal_guardian", "Infernal Guardian")
    assert "Double Slam" in infernal
    assert "block" in infernal["Double Slam"].mitigation.casefold()

    warden = _strategy("warden_of_the_shrine", "Warden of the Shrine")
    assert "Berserker Frenzy" in warden
    assert "step outside" in warden["Berserker Frenzy"].mitigation.casefold()
    assert "Burning Field and Clones" in warden
    assert "kill the summoned clones" in warden["Burning Field and Clones"].mitigation.casefold()

    erthas = _strategy("razor_master_erthas", "Razor Master Erthas")
    assert "Lava Pitch" in erthas
    assert "Blazing Arrow" in erthas
    assert "river" in erthas["Blazing Arrow"].mitigation.casefold()
    assert "Summon Flame Atronach" in erthas


def test_crypt_of_hearts_i_progression_bosses_have_reviewed_plans():
    siniel = _strategy("archmaster_siniel", "Archmaster Siniel")
    assert "Ground AoE" in siniel
    assert "move out" in siniel["Ground AoE"].mitigation.casefold()
    assert "Damage Shield and Zombies" in siniel

    leviathan = _strategy("death_s_leviathan", "Death's Leviathan")
    assert "Charge" in leviathan
    assert "nearby wall" in leviathan["Charge"].mitigation.casefold()
    assert "Burst" in leviathan
    assert "block or dodge roll" in leviathan["Burst"].mitigation.casefold()

    twins = _strategy("ilambris_twins", "Ilambris Twins")
    assert "Athor Heavy Attack" in twins
    assert "block" in twins["Athor Heavy Attack"].mitigation.casefold()
    assert "Survivor Enrage" in twins
    assert "similar health" in twins["Survivor Enrage"].mitigation.casefold()
