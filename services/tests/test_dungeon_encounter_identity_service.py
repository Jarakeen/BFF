from pathlib import Path

import json
import pytest

from services.dungeon_encounter_identity_service import (
    DungeonEncounterIdentityError,
    dungeon_encounters_for_content,
    load_dungeon_encounter_identities,
)


def _write(tmp_path: Path, rows, *, name: str = "dungeon_encounter_identity.json") -> None:
    (tmp_path / name).write_text(
        json.dumps({"schema_version": 1, "encounters": rows}), encoding="utf-8"
    )


def _row(**overrides):
    row = {
        "content_id": "new_dungeon",
        "content_name": "New Dungeon",
        "release_year": 2025,
        "release_update": 47,
        "release_pack": "Pack",
        "encounter_id": "boss",
        "display_name": "Boss",
        "member_ids": ["boss"],
    }
    row.update(overrides)
    return row


def test_release_sort_is_newest_first_and_launch_update_zero_is_valid(tmp_path):
    _write(
        tmp_path,
        [
            _row(),
            _row(
                content_id="launch",
                content_name="Launch",
                release_year=2014,
                release_update=0,
                encounter_id="launch_boss",
                display_name="Launch Boss",
                member_ids=["launch_boss"],
            ),
        ],
    )
    rows = load_dungeon_encounter_identities(tmp_path)
    assert [row.encounter_id for row in rows] == ["boss", "launch_boss"]
    assert rows[-1].release_key == (2014, 0)


def test_negative_release_update_fails_closed(tmp_path):
    _write(tmp_path, [_row(release_update=-1)])
    with pytest.raises(DungeonEncounterIdentityError, match="release_update.*non-negative"):
        load_dungeon_encounter_identities(tmp_path)


def test_grouped_final_encounter_keeps_members_under_one_fight(tmp_path):
    _write(
        tmp_path,
        [
            _row(
                encounter_id="talen_lah",
                display_name="Talen-Lah and Bar-Sakka",
                member_ids=["talen_lah", "bar_sakka"],
            )
        ],
    )
    row = load_dungeon_encounter_identities(tmp_path)[0]
    assert row.member_ids == ("talen_lah", "bar_sakka")
    assert row.is_grouped is True
    assert row.primary_member_id == "talen_lah"


def test_content_lookup_accepts_content_name_or_id(tmp_path):
    _write(tmp_path, [_row(content_id="naj_caldeesh", content_name="Naj-Caldeesh")])
    assert dungeon_encounters_for_content(tmp_path, "Naj-Caldeesh")[0].encounter_id == "boss"
    assert dungeon_encounters_for_content(tmp_path, "naj_caldeesh")[0].encounter_id == "boss"


def test_identity_shards_merge_under_one_contract(tmp_path):
    _write(tmp_path, [_row()])
    _write(
        tmp_path,
        [
            _row(
                content_id="launch",
                content_name="Launch",
                release_year=2014,
                release_update=0,
                encounter_id="launch_boss",
                display_name="Launch Boss",
                member_ids=["launch_boss"],
            )
        ],
        name="dungeon_encounter_identity_launch.json",
    )
    assert {row.encounter_id for row in load_dungeon_encounter_identities(tmp_path)} == {
        "boss",
        "launch_boss",
    }


def test_duplicate_reviewed_encounter_ids_fail_closed_across_shards(tmp_path):
    row = _row()
    _write(tmp_path, [row])
    _write(tmp_path, [row], name="dungeon_encounter_identity_launch.json")
    with pytest.raises(DungeonEncounterIdentityError, match="duplicate dungeon encounter id"):
        load_dungeon_encounter_identities(tmp_path)


def test_checked_in_registry_keeps_reviewed_progression_counts_and_chronology():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = load_dungeon_encounter_identities(data_root)
    by_content: dict[str, list] = {}
    for row in rows:
        by_content.setdefault(row.content_id, []).append(row)

    expected_counts = {
        "naj_caldeesh": 3,
        "black_gem_foundry": 3,
        "exiled_redoubt": 3,
        "lep_seclusa": 3,
        "oathsworn_pit": 3,
        "bedlam_veil": 3,
        "bal_sunnar": 3,
        "scrivener_s_hall": 3,
        "earthen_root_enclave": 3,
        "graven_deep": 3,
        "coral_aerie": 3,
        "shipwright_s_regret": 3,
        "red_petal_bastion": 3,
        "the_dread_cellar": 3,
        "black_drake_villa": 3,
        "the_cauldron": 4,
        "castle_thorn": 5,
        "stone_garden": 3,
        "icereach": 5,
        "unhallowed_grave": 5,
        "moongrave_fane": 5,
        "lair_of_maarselok": 5,
        "depths_of_malatar": 5,
        "frostvault": 5,
        "moon_hunter_keep": 5,
        "march_of_sacrifices": 5,
        "fang_lair": 5,
        "scalecaller_peak": 5,
        "bloodroot_forge": 6,
        "falkreath_hold": 5,
        "cradle_of_shadows": 5,
        "ruins_of_mazzatun": 4,
        "imperial_city_prison": 6,
        "white_gold_tower": 4,
        "city_of_ash_ii": 3,
        "crypt_of_hearts_ii": 3,
        "fungal_grotto_ii": 3,
        "spindleclutch_ii": 3,
        "the_banished_cells_ii": 3,
        "darkshade_caverns_ii": 3,
        "elden_hollow_ii": 3,
        "wayrest_sewers_ii": 3,
        "fungal_grotto_i": 2,
        "spindleclutch_i": 2,
        "the_banished_cells_i": 2,
    }
    assert {key: len(value) for key, value in by_content.items()} == expected_counts

    assert {row.release_key for row in rows} == {
        (2025, 47),
        (2025, 45),
        (2024, 41),
        (2023, 37),
        (2022, 35),
        (2022, 33),
        (2021, 31),
        (2021, 29),
        (2020, 27),
        (2020, 25),
        (2019, 23),
        (2019, 21),
        (2018, 19),
        (2018, 17),
        (2017, 15),
        (2016, 11),
        (2015, 7),
        (2014, 5),
        (2014, 2),
        (2014, 0),
    }
    assert rows[0].release_key == (2025, 47)
    assert rows[-1].release_key == (2014, 0)
    assert len(rows) == 167


def test_checked_in_registry_preserves_grouped_encounter_identities():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = load_dungeon_encounter_identities(data_root)
    by_id = {row.encounter_id: row for row in rows}

    assert by_id["talen_lah"].member_ids == ("talen_lah", "bar_sakka")
    assert by_id["artifact_bearers"].member_ids == (
        "eliam_merick",
        "ihudir",
        "liramindrel",
    )
    assert by_id["icereach_coven_boss"].member_ids == (
        "mother_ciannait",
        "sister_gohlla",
        "sister_hiti",
        "sister_bani",
        "sister_maefyn",
    )
    assert by_id["wyrd_sisters"].member_ids == (
        "wyress_rangifer",
        "wyress_strigidae",
        "wyress_ursus",
    )
    assert by_id["cadaverous_menagerie"].member_ids == (
        "cadaverous_bear",
        "cadaverous_guar",
        "cadaverous_senche_tiger",
    )
    assert by_id["ilambris_amalgam"].member_ids == (
        "ilambris_athor",
        "ilambris_zaven",
        "ilambris_amalgam",
    )
    assert by_id["allene_pellingare"].member_ids == (
        "allene_pellingare",
        "varaine_pellingare",
    )


def test_launch_veteran_slice_contains_only_conqueror_progression_encounters():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = load_dungeon_encounter_identities(data_root)
    by_content: dict[str, set[str]] = {}
    for row in rows:
        by_content.setdefault(row.content_id, set()).add(row.encounter_id)

    assert by_content["fungal_grotto_ii"] == {
        "gamyne_bandu",
        "spawn_of_mephala",
        "vila_theran",
    }
    assert by_content["spindleclutch_ii"] == {
        "bloodspawn_creature",
        "praxin_douare",
        "vorenor_winterbourne",
    }
    assert by_content["the_banished_cells_ii"] == {
        "maw_of_the_infernal",
        "keeper_imiril",
        "high_kinlord_rilis_banished_cells_ii",
    }
    assert by_content["darkshade_caverns_ii"] == {
        "transmuted_hive_lord",
        "grobull_the_transmuted",
        "the_engine_guardian",
    }
    assert by_content["elden_hollow_ii"] == {
        "dark_root",
        "murklight",
        "bogdan_the_nightflame",
    }
    assert by_content["wayrest_sewers_ii"] == {
        "malubeth_the_scourger",
        "garron_the_returned",
        "allene_pellingare",
    }

    all_ids = {row.encounter_id for row in rows}
    assert not {
        "dunmer",
        "spider_daedra",
        "gargoyle",
        "wraith",
        "fighters_guild",
        "nord",
        "draining_scrib",
        "sedating_scrib",
        "netch",
        "dwemer_spider",
        "spriggan",
        "lurcher",
        "daedric_titan",
        "harvester",
        "lich",
        "investigator_garron",
        "varaine_pellingare",
    } & all_ids


def test_launch_starter_slice_contains_only_vanquisher_progression_encounters():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = load_dungeon_encounter_identities(data_root)
    by_content: dict[str, set[str]] = {}
    for row in rows:
        by_content.setdefault(row.content_id, set()).add(row.encounter_id)

    assert by_content["fungal_grotto_i"] == {
        "war_chief_ozozai",
        "kra_gh_the_dreugh_king",
    }
    assert by_content["spindleclutch_i"] == {
        "swarm_mother",
        "the_whisperer",
    }
    assert by_content["the_banished_cells_i"] == {
        "shadowrend",
        "high_kinlord_rilis_banished_cells_i",
    }


def test_known_reviewed_semantic_import_gaps_stay_explicit():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = load_dungeon_encounter_identities(data_root)
    all_ids = {row.encounter_id for row in rows}
    known_missing_raw = {
        "icestalker",
        "lizabet_charnis",
        "doylemish_ironheart",
        "mathgamain",
        "stoneheart",
        "gherig_bullblood",
        "morrigh_bullblood",
        "deathlord_bjarfrud_skjoralmor",
        "sithera",
        "votary_of_velidreth",
        "zatzu_the_spine_breaker",
        "overfiend",
        "gravelight_sentry",
        "lord_wardens_council",
        "elite_guard",
    }
    assert known_missing_raw <= all_ids
    for encounter_id in known_missing_raw:
        assert not (data_root / "eso_info" / "bosses" / f"{encounter_id}.json").exists()
