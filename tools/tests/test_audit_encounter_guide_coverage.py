from pathlib import Path

from services.encounter_boss_guide import EncounterBossGuideService
from tools.audit_encounter_guide_coverage import (
    EncounterGuideCoverageRow,
    _canonical_phase_count,
    _content_key,
    _include_content,
    _line,
    _parse_args,
    build_coverage_rows,
)


def test_coverage_row_prefers_canonical_timeline_when_present():
    row = EncounterGuideCoverageRow(encounter_id="boss", content_name="Trial", encounter_name="Boss", canonical_timeline_rows=3, reviewed_timeline_rows=5, strategy_rows=4)
    assert row.effective_timeline_source == "canonical"
    assert row.timeline_missing is False
    assert row.strategy_missing is False


def test_coverage_row_uses_reviewed_fallback_when_canonical_timeline_is_missing():
    row = EncounterGuideCoverageRow(encounter_id="boss", content_name="Trial", encounter_name="Boss", canonical_timeline_rows=0, reviewed_timeline_rows=2, strategy_rows=1)
    assert row.effective_timeline_source == "reviewed_fallback"
    assert row.timeline_missing is False
    assert row.strategy_missing is False


def test_coverage_row_uses_reviewed_fallback_when_canonical_persistence_is_unavailable():
    row = EncounterGuideCoverageRow(encounter_id="boss", content_name="Dungeon", encounter_name="Boss", canonical_timeline_rows=None, reviewed_timeline_rows=2, strategy_rows=1)
    text = _line(row)
    assert row.effective_timeline_source == "reviewed_fallback"
    assert row.timeline_missing is False
    assert "canonical=unavailable" in text


def test_canonical_phase_count_marks_missing_database_unavailable(tmp_path: Path):
    service = EncounterBossGuideService(tmp_path / "missing.db")
    assert _canonical_phase_count(service, ("boss",)) is None


def test_coverage_row_reports_missing_timeline_and_strategy():
    row = EncounterGuideCoverageRow(encounter_id="boss", content_name="Trial", encounter_name="Boss", canonical_timeline_rows=0, reviewed_timeline_rows=0, strategy_rows=0)
    text = _line(row)
    assert row.timeline_missing is True
    assert row.strategy_missing is True
    assert "MISSING TIMELINE" in text
    assert "MISSING STRATEGY" in text


def test_trial_scope_reuses_known_trial_names_and_normalizes_leading_the():
    assert _content_key("The Halls of Fabrication") == "halls of fabrication"
    assert _include_content("Halls of Fabrication", trials_only=True) is True
    assert _include_content("Dreadsail Reef", trials_only=True) is True
    assert _include_content("Arx Corinium", trials_only=True) is False


def test_all_content_scope_keeps_non_trial_content():
    assert _include_content("Arx Corinium", trials_only=False) is True


def test_audit_defaults_to_reviewed_raid_scope():
    args = _parse_args([])
    assert args.dungeons is False
    assert args.raw_trial_records is False
    assert args.all_content is False


def test_audit_scope_flags_are_mutually_distinct():
    dungeon_args = _parse_args(["--dungeons"])
    trial_args = _parse_args(["--raw-trial-records"])
    all_args = _parse_args(["--all-content"])
    assert dungeon_args.dungeons is True
    assert dungeon_args.raw_trial_records is False
    assert dungeon_args.all_content is False
    assert trial_args.dungeons is False
    assert trial_args.raw_trial_records is True
    assert trial_args.all_content is False
    assert all_args.dungeons is False
    assert all_args.raw_trial_records is False
    assert all_args.all_content is True


def test_checked_in_dungeon_scope_is_newest_first_through_launch_normal_slice():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = build_coverage_rows(data_root, scope="dungeon")

    assert len(rows) == 194
    assert {(row.release_year, row.release_update) for row in rows} == {
        (2025, 47), (2025, 45), (2024, 41), (2023, 37),
        (2022, 35), (2022, 33), (2021, 31), (2021, 29),
        (2020, 27), (2020, 25), (2019, 23), (2019, 21),
        (2018, 19), (2018, 17), (2017, 15), (2016, 11), (2015, 7),
        (2014, 5), (2014, 2), (2014, 0),
    }
    assert (rows[0].release_year, rows[0].release_update) == (2025, 47)
    assert (rows[-1].release_year, rows[-1].release_update) == (2014, 0)

    assert {row.content_name for row in rows} == {
        "Black Gem Foundry", "Naj-Caldeesh", "Exiled Redoubt", "Lep Seclusa",
        "Oathsworn Pit", "Bedlam Veil", "Bal Sunnar", "Scrivener's Hall",
        "Earthen Root Enclave", "Graven Deep", "Coral Aerie", "Shipwright's Regret",
        "Red Petal Bastion", "The Dread Cellar", "Black Drake Villa", "The Cauldron",
        "Castle Thorn", "Stone Garden", "Icereach", "Unhallowed Grave",
        "Moongrave Fane", "Lair of Maarselok", "Depths of Malatar", "Frostvault",
        "Moon Hunter Keep", "March of Sacrifices", "Fang Lair", "Scalecaller Peak",
        "Bloodroot Forge", "Falkreath Hold", "Cradle of Shadows", "Ruins of Mazzatun",
        "Imperial City Prison", "White-Gold Tower", "City of Ash II", "Crypt of Hearts II",
        "Fungal Grotto II", "Spindleclutch II", "The Banished Cells II",
        "Darkshade Caverns II", "Elden Hollow II", "Wayrest Sewers II",
        "Fungal Grotto I", "Spindleclutch I", "The Banished Cells I",
        "Darkshade Caverns I", "Elden Hollow I", "Wayrest Sewers I",
        "Arx Corinium", "City of Ash I", "Crypt of Hearts I",
        "Volenfell", "Tempest Island", "Blackheart Haven",
    }

    assert {row.encounter_id for row in rows} == {
        "poxito", "voskrona_stonehulk_poxito", "talen_lah",
        "quarrymaster_saldezaar", "black_gem_monstrosity", "high_soulbinder_vykand",
        "executioner_jerensi", "prime_sorcerer_vandorallen", "squall_of_retribution",
        "garvin_the_tracker", "noriwen", "orpheon_the_tactician",
        "packmaster_rethelros", "anthelmir_s_construct", "aradros_the_awakened",
        "shattered_champion", "darkshard", "the_blind",
        "kovan_giryon", "roksa_the_warped", "matriarch_lladi_telvanni",
        "riftmaster_naqri", "ozezan_the_inferno", "valinna",
        "corruption_of_stone", "corruption_of_root", "archdruid_devyric",
        "the_euphotic_gatekeeper", "varzunon", "zelvraak_the_unbreathing",
        "maligalig", "sarydil", "varallion",
        "foreman_bradiggan", "nazaray", "captain_numirril",
        "rogerain_the_sly", "artifact_bearers", "prior_thierric_sarazen",
        "scorion_broodlord", "cyronin_artellian", "magma_incarnate",
        "kinras_ironeye", "captain_geminus", "pyroturge_encratis",
        "oxblood_the_depraved", "taskmaster_viccia", "molten_guardian", "baron_zaudrus",
        "dread_tindulra", "blood_twilight", "vaduroth", "talfyg", "lady_thorn",
        "exarch_kraglen", "stone_behemoth", "arkasis_the_mad_alchemist",
        "kjarg_the_tuskscraper", "sister_skelga", "vearogh_the_shambler", "stormborn_revenant", "icereach_coven_boss",
        "hakgrym_the_howler", "keeper_of_the_kiln", "eternal_aegis", "ondagore_the_mad", "kjalnar_tombskald",
        "risen_ruins", "dro_zakar", "kujo_kethba", "nisaazda", "grundwulf",
        "selene", "maarselok_in_flight", "azureblight_cancroid", "maarselok_on_his_perch", "maarselok_in_his_roost",
        "the_scavenging_maw", "the_weeping_woman", "dark_orb", "king_narilmor", "symphony_of_blades",
        "icestalker", "warlord_tzogvin", "vault_protector", "rizzuk_bonechill", "the_stonekeeper",
        "jailer_melitus", "hedge_maze_guardian", "mylenne_moon_caller", "archivist_ernarde", "vykosa_the_ascendant",
        "wyrd_sisters", "aghaedh_of_the_solstice", "dagrund_the_bulky", "tarcyr", "balorgh",
        "lizabet_charnis", "cadaverous_menagerie", "caluurion", "ulfnor", "orryn_the_black",
        "orzun_the_foul_smelling", "doylemish_ironheart", "matriarch_aldis", "plague_concocter_mortieu", "zaan_the_scalecaller",
        "mathgamain", "caillaoife", "stoneheart", "galchobhar", "gherig_bullblood", "earthgore_amalgam",
        "morrigh_bullblood", "siege_mammoth", "cernunnon", "deathlord_bjarfrud_skjoralmor", "domihaus_the_bloody_horned",
        "sithera", "khephidaen", "votary_of_velidreth", "dranos_velador", "velidreth",
        "zatzu_the_spine_breaker", "mighty_chudan", "xal_nur_the_slaver", "tree_minder_na_kesh",
        "overfiend", "ibomez_the_flesh_sculptor", "gravelight_sentry", "flesh_abomination_imperial_city_prison", "lord_wardens_council", "lord_warden_dusk",
        "the_adjudicator", "elite_guard", "the_planar_inhibitor", "molag_kena",
        "horvantud_the_fire_maw", "ash_titan_city_of_ash_ii", "valkyn_skoria_person",
        "ruzozuzalpamaz", "ilambris_amalgam", "nerien_eth",
        "gamyne_bandu", "spawn_of_mephala", "vila_theran",
        "bloodspawn_creature", "praxin_douare", "vorenor_winterbourne",
        "maw_of_the_infernal", "keeper_imiril", "high_kinlord_rilis_banished_cells_ii",
        "transmuted_hive_lord", "grobull_the_transmuted", "the_engine_guardian",
        "dark_root", "murklight", "bogdan_the_nightflame",
        "malubeth_the_scourger", "garron_the_returned", "allene_pellingare",
        "war_chief_ozozai", "kra_gh_the_dreugh_king",
        "swarm_mother", "the_whisperer",
        "shadowrend", "high_kinlord_rilis_banished_cells_i",
        "foreman_llothan", "the_hive_lord", "sentinel_of_rkugamz",
        "akash_gra_mal", "chokethorn", "canonreeve_oraneth",
        "investigator_garron", "varaine_pellingare", "allene_pellingare_wayrest_sewers_i",
        "ganakton_the_tempest", "sliklenia_the_songstress", "sellistrix_the_lamia_queen",
        "infernal_guardian", "warden_of_the_shrine", "razor_master_erthas",
        "archmaster_siniel", "death_s_leviathan", "ilambris_twins",
        "quintus_verres", "tremorscale", "guardian_council",
        "valaran_stormcaller", "stormfist", "stormreeve_neidir",
        "atarus", "roost_mother", "captain_blackheart",
    }
