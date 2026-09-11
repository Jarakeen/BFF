from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_overfiend_projection_has_flurry_and_add_control():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("overfiend", "Overfiend")
    s = _strategy(p)
    assert "Flurry" in s
    assert "faced away" in s["Flurry"].mitigation.casefold()
    assert "Health-Triggered Adds" in s


def test_ibomez_projection_has_flesh_atronach_priority():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("ibomez_the_flesh_sculptor", "Ibomez the Flesh Sculptor")
    assert "Flesh Atronachs" in _strategy(p)


def test_gravelight_projection_has_knockback_and_necromancers():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("gravelight_sentry", "Gravelight Sentry")
    s = _strategy(p)
    assert {"Spin Knockback", "Necromancer Adds"} <= set(s)
    assert "poisonous water" in s["Spin Knockback"].mitigation.casefold()


def test_flesh_abomination_projection_preserves_center():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("flesh_abomination_imperial_city_prison", "Flesh Abomination")
    s = _strategy(p)
    assert "Arena Pressure" in s
    assert "center" in s["Arena Pressure"].mitigation.casefold()


def test_lord_warden_council_projection_has_healer_interrupt():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("lord_wardens_council", "Lord Warden's Council")
    s = _strategy(p)
    assert {"Healer Bodyguard", "Council Stack"} <= set(s)
    assert "interrupt" in s["Healer Bodyguard"].mitigation.casefold()


def test_lord_warden_projection_has_portal_survival():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("lord_warden_dusk", "Lord Warden Dusk")
    assert "Portal Survival" in _labels(p)
    s = _strategy(p)
    assert {"Darklight Burst", "Portal Synergy"} <= set(s)


def test_adjudicator_projection_has_spacing_and_zombie_control():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("the_adjudicator", "The Adjudicator")
    s = _strategy(p)
    assert {"Zombie Adds", "Targeted Mechanics Spacing"} <= set(s)


def test_elite_guard_projection_has_kill_order_and_healer_interrupt():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("elite_guard", "Elite Guard")
    s = _strategy(p)
    assert {"Healer Guard", "Guard Kill Order"} <= set(s)
    assert "interrupt" in s["Healer Guard"].mitigation.casefold()


def test_planar_inhibitor_projection_has_pinion_and_portal_cycles():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("the_planar_inhibitor", "The Planar Inhibitor")
    assert {"Pinion Control", "Blue-Flame Kite"} <= _labels(p)
    s = _strategy(p)
    assert {"Portal Duty", "Flame Bursts"} <= set(s)


def test_molag_kena_projection_has_second_shield_and_double_wall_execute():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("molag_kena", "Molag Kena")
    assert {"Shield Adds I", "Shield Adds II", "Double-Wall Execute"} <= _labels(p)
    s = _strategy(p)
    assert {"Lightning Spin", "Shielding Adds"} <= set(s)
