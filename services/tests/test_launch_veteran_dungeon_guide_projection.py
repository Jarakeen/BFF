from pathlib import Path

from services.encounter_guide_evidence_projection_service import EncounterGuideEvidenceProjectionService


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_gamyne_has_execution_and_tether_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("gamyne_bandu", "Gamyne Bandu"))
    assert "Shadow Execution" in s and "pinned player" in s["Shadow Execution"].mitigation.casefold()
    assert "Shadow Chains" in s and "move apart" in s["Shadow Chains"].mitigation.casefold()


def test_spawn_of_mephala_has_portal_and_beam_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("spawn_of_mephala", "Spawn of Mephala"))
    assert "Portal Pull" in s and "spider room" in s["Portal Pull"].mitigation.casefold()
    assert "Tracking Beam" in s


def test_vila_theran_has_corruption_and_channel_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("vila_theran", "Vila Theran"))
    assert "Growing Corruption" in s and "safe space" in s["Growing Corruption"].mitigation.casefold()
    assert "Channeled Shadow" in s


def test_bloodspawn_has_cave_in_and_rocks():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("bloodspawn_creature", "Bloodspawn"))
    assert "Cave-In" in s and "block" in s["Cave-In"].mitigation.casefold()
    assert "Crushing Rocks" in s


def test_praxin_has_add_waves_and_harrowing_ring():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("praxin_douare", "Praxin Douare")
    assert {"Ghost Add Waves", "Praxin Wraith Phase"} <= _labels(p)
    assert "boundary" in _strategy(p)["Harrowing Ring"].mitigation.casefold()


def test_vorenor_has_strikes_and_sacrifices():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("vorenor_winterbourne", "Vorenor Winterbourne"))
    assert "Blood Strike" in s and "block" in s["Blood Strike"].mitigation.casefold()
    assert "Sacrifices" in s


def test_maw_has_frontal_and_heavy_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("maw_of_the_infernal", "Maw of the Infernal"))
    assert "Fire Breath" in s and "away" in s["Fire Breath"].mitigation.casefold()
    assert "Heavy Attack" in s


def test_keeper_imiril_has_three_portal_waves_and_return_burst():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("keeper_imiril", "Keeper Imiril")
    assert {"Banekin Portal", "Twilight Portal", "Clannfear Portal"} <= _labels(p)
    assert "Portal Return Burst" in _strategy(p)


def test_rilis_has_feasts_bubble_and_hard_mode():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("high_kinlord_rilis_banished_cells_ii", "High Kinlord Rilis"))
    assert "Feasts" in s and "before they reach rilis" in s["Feasts"].mitigation.casefold()
    assert "Colored Bubble Curse" in s
    assert "Hard Mode Daedroths" in s


def test_hive_lord_has_shield_break_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("transmuted_hive_lord", "Transmuted Hive Lord"))
    assert "Cave In" in s and "shield" in s["Cave In"].mitigation.casefold()
    assert "Quaking Smash" in s


def test_grobull_has_shield_and_vulnerability_windows():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("grobull_the_transmuted", "Grobull the Transmuted")
    assert {"Shielded Netch Phase", "Vulnerability Window"} <= _labels(p)
    assert "Netchling Waves" in _strategy(p)


def test_engine_guardian_has_three_color_modes():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("the_engine_guardian", "The Engine Guardian")
    assert {"Red Fire Phase", "Green Poison Phase", "Blue Lightning Phase"} <= _labels(p)
    assert "red means move" in _strategy(p)["Color-Coded Modes"].mitigation.casefold()


def test_dark_root_has_spread_and_resource_plan():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("dark_root", "Dark Root"))
    assert "Radiated Beam" in s and "spread" in s["Radiated Beam"].mitigation.casefold()
    assert "Hoarvor Resource Buffs" in s


def test_murklight_has_darkness_safe_zone():
    p = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("murklight", "Murklight")
    assert "Darkness Safe-Zone Check" in _labels(p)
    assert "glowing white circle" in _strategy(p)["Darkness Safe Circle"].mitigation.casefold()


def test_bogdan_has_add_priority_and_jump_block():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("bogdan_the_nightflame", "Bogdan the Nightflame"))
    assert "Shadow Adds" in s and "mind-control" in s["Shadow Adds"].mitigation.casefold()
    assert "Healer Adds" in s and "interrupt" in s["Healer Adds"].mitigation.casefold()
    assert "Nightflame Jump" in s


def test_malubeth_has_two_player_lift_release():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("malubeth_the_scourger", "Malubeth the Scourger"))
    assert "Lift" in s and "two free players" in s["Lift"].mitigation.casefold()
    assert "Ground AoEs" in s


def test_garron_has_soul_priority_and_group_heal_check():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("garron_the_returned", "Garron the Returned"))
    assert "Escaped Souls" in s and "immediately" in s["Escaped Souls"].mitigation.casefold()
    assert "Consume Life" in s and "stack for healing" in s["Consume Life"].mitigation.casefold()


def test_pellingare_twins_have_group_control_and_zombie_condition():
    s = _strategy(EncounterGuideEvidenceProjectionService(DATA_ROOT).get("allene_pellingare", "Varaine and Allene Pellingare"))
    assert "Twin Control" in s and "both twins" in s["Twin Control"].mitigation.casefold()
    assert "Zombie Hard Mode" in s and "fifteen zombies" in s["Zombie Hard Mode"].mitigation.casefold()
