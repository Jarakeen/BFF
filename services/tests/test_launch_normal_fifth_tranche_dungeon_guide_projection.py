from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _strategy(encounter_id: str, name: str):
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(encounter_id, name)
    assert projection.timeline
    return {row.mechanic: row for row in projection.strategy}


def test_direfrost_keep_progression_bosses_have_reviewed_plans():
    guardian = _strategy("guardian_of_the_flame", "Guardian of the Flame")
    assert "Heavy Attack" in guardian
    assert "block" in guardian["Heavy Attack"].mitigation.casefold()

    iceheart = _strategy("iceheart", "Iceheart")
    assert "Frontal Clobber" in iceheart
    assert "faced away" in iceheart["Frontal Clobber"].mitigation.casefold()
    assert "Arctic Awakening" in iceheart
    assert "skeleton" in iceheart["Arctic Awakening"].mitigation.casefold()

    drodda = _strategy("drodda_of_icereach", "Drodda of Icereach")
    assert "Life Drain" in drodda
    assert "break free" in drodda["Life Drain"].mitigation.casefold()
    assert "Frost Atronachs" in drodda


def test_selenes_web_progression_bosses_have_reviewed_plans():
    longclaw = _strategy("longclaw", "Longclaw")
    assert "Spirit Panthers" in longclaw
    assert "control" in longclaw["Spirit Panthers"].mitigation.casefold()
    assert "Volley and Poison" in longclaw

    foulhide = _strategy("foulhide", "Foulhide")
    assert "Interruptible Cast" in foulhide
    assert "bash" in foulhide["Interruptible Cast"].mitigation.casefold()

    selene = _strategy("selene_s_web", "Selene")
    assert "Webs and Ravens" in selene
    assert "move out" in selene["Webs and Ravens"].mitigation.casefold()
    assert "Bear Attack" in selene
    assert "faced away" in selene["Bear Attack"].mitigation.casefold()


def test_blessed_crucible_progression_units_have_reviewed_plans():
    pack = _strategy("the_pack", "The Pack")
    assert "Snagg Uppercut" in pack
    assert "block" in pack["Snagg Uppercut"].mitigation.casefold()
    assert "Nusana Fire Line" in pack
    assert "Dynus Channel" in pack
    assert "interrupt" in pack["Dynus Channel"].mitigation.casefold()

    beast_master = _strategy("the_beast_master", "The Beast Master")
    assert "Beetle Fire" in beast_master
    assert "Troll King Slam" in beast_master
    assert "stay reasonably close" in beast_master["Troll King Slam"].mitigation.casefold()

    lava_queen = _strategy("the_lava_queen", "The Lava Queen")
    assert "Atronach Immunity" in lava_queen
    assert "kill the atronachs" in lava_queen["Atronach Immunity"].mitigation.casefold()
    assert "Lava Queen Heavy Attack" in lava_queen
    assert "block" in lava_queen["Lava Queen Heavy Attack"].mitigation.casefold()
