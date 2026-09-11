from pathlib import Path

import json

from services.dungeon_encounter_identity_service import (
    DungeonEncounterIdentityError,
    dungeon_encounters_for_content,
    load_dungeon_encounter_identities,
)


def _write(tmp_path: Path, rows) -> None:
    (tmp_path / "dungeon_encounter_identity.json").write_text(
        json.dumps({"schema_version": 1, "encounters": rows}),
        encoding="utf-8",
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


def test_release_sort_is_newest_first(tmp_path):
    _write(
        tmp_path,
        [
            _row(
                content_id="old",
                content_name="Old",
                release_year=2024,
                release_update=43,
                encounter_id="old_boss",
                display_name="Old Boss",
                member_ids=["old_boss"],
            ),
            _row(),
        ],
    )

    rows = load_dungeon_encounter_identities(tmp_path)
    assert [row.encounter_id for row in rows] == ["boss", "old_boss"]


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

    assert len(by_content["naj_caldeesh"]) == 3
    assert len(by_content["black_gem_foundry"]) == 3
    assert len(by_content["exiled_redoubt"]) == 3
    assert len(by_content["lep_seclusa"]) == 3
    assert len(by_content["oathsworn_pit"]) == 3
    assert len(by_content["bedlam_veil"]) == 3
    assert {row.release_key for row in rows} == {(2025, 47), (2025, 45), (2024, 41)}
    assert rows[0].release_key == (2025, 47)
    assert rows[-1].release_key == (2024, 41)

    naj = {row.encounter_id: row for row in by_content["naj_caldeesh"]}
    assert naj["talen_lah"].member_ids == ("talen_lah", "bar_sakka")
    assert "bar_sakka" not in {row.encounter_id for row in rows}

    oathsworn = {row.encounter_id: row for row in by_content["oathsworn_pit"]}
    assert oathsworn["packmaster_rethelros"].member_ids == (
        "packmaster_rethelros",
        "malthil",
    )
    assert oathsworn["anthelmir_s_construct"].member_ids == (
        "anthelmir_s_construct",
        "anthelmir",
    )
    assert "malthil" not in {row.encounter_id for row in rows}
    assert "anthelmir" not in {row.encounter_id for row in rows}

    bedlam_ids = {row.encounter_id for row in by_content["bedlam_veil"]}
    assert bedlam_ids == {"shattered_champion", "darkshard", "the_blind"}
    assert "crystal_atronach" not in {row.encounter_id for row in rows}
    assert "mind_terror" not in {row.encounter_id for row in rows}
