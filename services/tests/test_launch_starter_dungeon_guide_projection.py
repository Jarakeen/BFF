from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_ozozai_has_spread_and_heavy_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("war_chief_ozozai", "War Chief Ozozai"))
    assert "Daedric Blast" in s and "overlaps teammates" in s["Daedric Blast"].mitigation.casefold()
    assert "Haymaker" in s and "block" in s["Haymaker"].mitigation.casefold()


def test_kragh_has_flurry_and_lightning_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("kra_gh_the_dreugh_king", "Kra'gh the Dreugh King"))
    assert "Storm Flurry" in s and "block" in s["Storm Flurry"].mitigation.casefold()
    assert "Lightning Field" in s and "move out" in s["Lightning Field"].mitigation.casefold()


def test_swarm_mother_has_spider_and_leap_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("swarm_mother", "Swarm Mother"))
    assert "Summon Spiders" in s and "interrupt" in s["Summon Spiders"].mitigation.casefold()
    assert "Leap" in s and "restack" in s["Leap"].mitigation.casefold()


def test_whisperer_has_pull_and_explosion_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("the_whisperer", "The Whisperer"))
    assert "Web Pull" in s and "center pull" in s["Web Pull"].mitigation.casefold()
    assert "Daedric Explosion" in s and "personal spacing" in s["Daedric Explosion"].mitigation.casefold()


def test_shadowrend_has_clone_and_devour_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("shadowrend", "Shadowrend"))
    assert "Shadow Clone" in s and "immediately" in s["Shadow Clone"].mitigation.casefold()
    assert "Charge and Devour" in s and "interrupt" in s["Charge and Devour"].mitigation.casefold()


def test_rilis_has_feasts_fire_and_heavy_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("high_kinlord_rilis_banished_cells_i", "High Kinlord Rilis"))
    assert "Feasts" in s and "before they reach rilis" in s["Feasts"].mitigation.casefold()
    assert "Ghost Fire" in s and "step out" in s["Ghost Fire"].mitigation.casefold()
    assert "Heavy Blow" in s and "block" in s["Heavy Blow"].mitigation.casefold()
