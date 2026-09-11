from pathlib import Path

import json

from services.dungeon_encounter_identity_service import (
    DungeonEncounterIdentityError,
    dungeon_encounters_for_content,
    load_dungeon_encounter_identities,
)


def _write(tmp_path: Path, rows) -> None:
    (tmp_path / "dungeon_encounter_identity.json").write_text(
        json.dumps({"schema_version": 1, "encounters": rows}), encoding="utf-8"
    )


def _row(**overrides):
    row = {
        "content_id": "new_dungeon", "content_name": "New Dungeon",
        "release_year": 2025, "release_update": 47, "release_pack": "Pack",
        "encounter_id": "boss", "display_name": "Boss", "member_ids": ["boss"],
    }
    row.update(overrides)
    return row


def test_release_sort_is_newest_first(tmp_path):
    _write(tmp_path, [_row(content_id="old", content_name="Old", release_year=2024,
                           release_update=43, encounter_id="old_boss",
                           display_name="Old Boss", member_ids=["old_boss"]), _row()])
    rows = load_dungeon_encounter_identities(tmp_path)
    assert [row.encounter_id for row in rows] == ["boss", "old_boss"]


def test_grouped_final_encounter_keeps_members_under_one_fight(tmp_path):
    _write(tmp_path, [_row(encounter_id="talen_lah", display_name="Talen-Lah and Bar-Sakka",
                           member_ids=["talen_lah", "bar_sakka"])])
    row = load_dungeon_encounter_identities(tmp_path)[0]
    assert row.member_ids == ("talen_lah", "bar_sakka")
    assert row.is_grouped is True
    assert row.primary_member_id == "talen_lah"


def test_content_lookup_accepts_content_name_or_id(tmp_path):
    _write(tmp_path, [_row(content_id="naj_caldeesh", content_name="Naj-Caldeesh")])
    assert dungeon_encounters_for_content(tmp_path, "Naj-Caldeesh")[0].encounter_id == "boss"
    assert dungeon_encounters_for_content(tmp_path, "naj_caldeesh")[0].encounter_id == "boss"


def test_duplicate_reviewed_encounter_ids_fail_closed(tmp_path):
    row = _row()
    _write(tmp_path, [row, row])
    try:
        load_dungeon_encounter_identities(tmp_path)
    except DungeonEncounterIdentityError as exc:
        assert "duplicate dungeon encounter id" in str(exc)
    else:
        raise AssertionError("duplicate reviewed dungeon encounter ids must fail closed")


def test_checked_in_registry_keeps_newest_first_release_slices_and_main_encounters():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = load_dungeon_encounter_identities(data_root)
    by_content = {}
    for row in rows:
        by_content.setdefault(row.content_id, []).append(row)

    for content_id in (
        "naj_caldeesh", "black_gem_foundry", "exiled_redoubt", "lep_seclusa",
        "oathsworn_pit", "bedlam_veil", "bal_sunnar", "scrivener_s_hall",
        "earthen_root_enclave", "graven_deep", "coral_aerie", "shipwright_s_regret",
        "red_petal_bastion", "the_dread_cellar", "black_drake_villa", "stone_garden",
    ):
        assert len(by_content[content_id]) == 3
    assert len(by_content["the_cauldron"]) == 4
    assert len(by_content["castle_thorn"]) == 5
    assert len(by_content["icereach"]) == 5
    assert len(by_content["unhallowed_grave"]) == 5
    assert len(by_content["moongrave_fane"]) == 5
    assert len(by_content["lair_of_maarselok"]) == 5
    assert len(by_content["depths_of_malatar"]) == 5
    assert len(by_content["frostvault"]) == 5

    assert {row.release_key for row in rows} == {
        (2025, 47), (2025, 45), (2024, 41), (2023, 37), (2022, 35), (2022, 33),
        (2021, 31), (2021, 29), (2020, 27), (2020, 25), (2019, 23), (2019, 21),
    }
    assert rows[0].release_key == (2025, 47)
    assert rows[-1].release_key == (2019, 21)

    all_ids = {row.encounter_id for row in rows}

    naj = {row.encounter_id: row for row in by_content["naj_caldeesh"]}
    assert naj["talen_lah"].member_ids == ("talen_lah", "bar_sakka")
    assert "bar_sakka" not in all_ids

    oathsworn = {row.encounter_id: row for row in by_content["oathsworn_pit"]}
    assert oathsworn["packmaster_rethelros"].member_ids == ("packmaster_rethelros", "malthil")
    assert oathsworn["anthelmir_s_construct"].member_ids == ("anthelmir_s_construct", "anthelmir")
    assert "malthil" not in all_ids
    assert "anthelmir" not in all_ids

    assert {row.encounter_id for row in by_content["bedlam_veil"]} == {"shattered_champion", "darkshard", "the_blind"}
    assert "crystal_atronach" not in all_ids
    assert "mind_terror" not in all_ids

    assert {row.encounter_id for row in by_content["bal_sunnar"]} == {"kovan_giryon", "roksa_the_warped", "matriarch_lladi_telvanni"}
    assert "urvel_drath" not in all_ids
    assert "house_telvanni" not in all_ids

    scriveners = {row.encounter_id: row for row in by_content["scrivener_s_hall"]}
    assert set(scriveners) == {"riftmaster_naqri", "ozezan_the_inferno", "valinna"}
    assert scriveners["valinna"].member_ids == ("valinna", "lamikhai")
    assert "lamikhai" not in all_ids
    assert "infernium" not in all_ids
    assert "cartoqueen" not in all_ids

    assert {row.encounter_id for row in by_content["earthen_root_enclave"]} == {"corruption_of_stone", "corruption_of_root", "archdruid_devyric"}
    assert {row.encounter_id for row in by_content["graven_deep"]} == {"the_euphotic_gatekeeper", "varzunon", "zelvraak_the_unbreathing"}
    assert {row.encounter_id for row in by_content["coral_aerie"]} == {"maligalig", "sarydil", "varallion"}
    assert "iliata" not in all_ids and "mafremare" not in all_ids and "ofallo" not in all_ids and "kargaeda" not in all_ids
    assert {row.encounter_id for row in by_content["shipwright_s_regret"]} == {"foreman_bradiggan", "nazaray", "captain_numirril"}
    assert "wraith" not in all_ids and "spriggan" not in all_ids and "maormer" not in all_ids

    red_petal = {row.encounter_id: row for row in by_content["red_petal_bastion"]}
    assert set(red_petal) == {"rogerain_the_sly", "artifact_bearers", "prior_thierric_sarazen"}
    assert red_petal["artifact_bearers"].member_ids == ("eliam_merick", "ihudir", "liramindrel")
    assert "eliam_merick" not in all_ids and "ihudir" not in all_ids and "liramindrel" not in all_ids

    assert {row.encounter_id for row in by_content["the_dread_cellar"]} == {"scorion_broodlord", "cyronin_artellian", "magma_incarnate"}
    assert "scorion" not in all_ids and "ruinach" not in all_ids
    assert {row.encounter_id for row in by_content["black_drake_villa"]} == {"kinras_ironeye", "captain_geminus", "pyroturge_encratis"}
    assert "minotaur" not in all_ids and "true_sworn" not in all_ids and "sentinel_aksalaz" not in all_ids
    assert {row.encounter_id for row in by_content["the_cauldron"]} == {"oxblood_the_depraved", "taskmaster_viccia", "molten_guardian", "baron_zaudrus"}
    assert "ogrim" not in all_ids and "havocrel" not in all_ids
    assert {row.encounter_id for row in by_content["castle_thorn"]} == {"dread_tindulra", "blood_twilight", "vaduroth", "talfyg", "lady_thorn"}
    assert "grievous_twilight" not in all_ids and "wraith_of_crows" not in all_ids
    assert {row.encounter_id for row in by_content["stone_garden"]} == {"exarch_kraglen", "stone_behemoth", "arkasis_the_mad_alchemist"}

    icereach = {row.encounter_id: row for row in by_content["icereach"]}
    assert set(icereach) == {"kjarg_the_tuskscraper", "sister_skelga", "vearogh_the_shambler", "stormborn_revenant", "icereach_coven_boss"}
    assert icereach["icereach_coven_boss"].member_ids == ("mother_ciannait", "sister_gohlla", "sister_hiti", "sister_bani", "sister_maefyn")
    assert "giant" not in all_ids and "hagraven" not in all_ids and "flesh_atronach" not in all_ids and "reachmen" not in all_ids and "mother_ciannait" not in all_ids

    assert {row.encounter_id for row in by_content["unhallowed_grave"]} == {"hakgrym_the_howler", "keeper_of_the_kiln", "eternal_aegis", "ondagore_the_mad", "kjalnar_tombskald"}
    assert "lich" not in all_ids and "tzirzhalir" not in all_ids

    moongrave = {row.encounter_id: row for row in by_content["moongrave_fane"]}
    assert set(moongrave) == {"risen_ruins", "dro_zakar", "kujo_kethba", "nisaazda", "grundwulf"}
    assert moongrave["nisaazda"].member_ids == ("nisaazda", "grundwulf")
    assert "stone_atronach" not in all_ids and "pahmar_raht" not in all_ids and "gargoyle" not in all_ids

    maarselok = {row.encounter_id: row for row in by_content["lair_of_maarselok"]}
    assert set(maarselok) == {"selene", "maarselok_in_flight", "azureblight_cancroid", "maarselok_on_his_perch", "maarselok_in_his_roost"}
    assert maarselok["maarselok_in_flight"].member_ids == ("maarselok",)
    assert maarselok["maarselok_on_his_perch"].member_ids == ("maarselok",)
    assert maarselok["maarselok_in_his_roost"].member_ids == ("maarselok", "selene")

    assert {row.encounter_id for row in by_content["depths_of_malatar"]} == {
        "the_scavenging_maw", "the_weeping_woman", "dark_orb", "king_narilmor", "symphony_of_blades"
    }
    assert "hunger" not in all_ids and "frozen" not in all_ids and "nereid" not in all_ids and "blessed_sentinel" not in all_ids

    frostvault = {row.encounter_id: row for row in by_content["frostvault"]}
    assert set(frostvault) == {"icestalker", "warlord_tzogvin", "vault_protector", "rizzuk_bonechill", "the_stonekeeper"}
    assert frostvault["icestalker"].member_ids == ("icestalker",)
    assert not (data_root / "eso_info" / "bosses" / "icestalker.json").exists()
    assert "riekling" not in all_ids and "avalanche" not in all_ids and "dwarven_colossus" not in all_ids and "wrathstone" not in all_ids
