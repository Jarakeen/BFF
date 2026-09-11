from pathlib import Path

import json

from services.raid_encounter_identity_service import (
    RaidEncounterIdentityError,
    load_raid_encounter_identities,
    raid_encounters_for_content,
)


def _write(tmp_path: Path, rows) -> None:
    (tmp_path / "raid_encounter_identity.json").write_text(
        json.dumps({"schema_version": 1, "encounters": rows}),
        encoding="utf-8",
    )


def test_grouped_encounter_identity_keeps_members_under_one_fight(tmp_path):
    _write(
        tmp_path,
        [
            {
                "content_id": "dreadsail_reef",
                "content_name": "Dreadsail Reef",
                "encounter_id": "lylanar_turlassil",
                "display_name": "Lylanar and Turlassil",
                "member_ids": ["lylanar", "turlassil"],
            }
        ],
    )

    row = load_raid_encounter_identities(tmp_path)[0]
    assert row.encounter_id == "lylanar_turlassil"
    assert row.member_ids == ("lylanar", "turlassil")
    assert row.is_grouped is True
    assert row.primary_member_id == "lylanar"


def test_content_lookup_accepts_content_name_or_id(tmp_path):
    _write(
        tmp_path,
        [
            {
                "content_id": "sunspire",
                "content_name": "Sunspire",
                "encounter_id": "lokkestiiz",
                "display_name": "Lokkestiiz",
                "member_ids": ["lokkestiiz"],
            }
        ],
    )

    assert raid_encounters_for_content(tmp_path, "Sunspire")[0].encounter_id == "lokkestiiz"
    assert raid_encounters_for_content(tmp_path, "sunspire")[0].encounter_id == "lokkestiiz"


def test_duplicate_reviewed_encounter_ids_fail_closed(tmp_path):
    row = {
        "content_id": "trial",
        "content_name": "Trial",
        "encounter_id": "boss",
        "display_name": "Boss",
        "member_ids": ["boss"],
    }
    _write(tmp_path, [row, row])

    try:
        load_raid_encounter_identities(tmp_path)
    except RaidEncounterIdentityError as exc:
        assert "duplicate raid encounter id" in str(exc)
    else:
        raise AssertionError("duplicate reviewed raid encounter ids must fail closed")


def test_checked_in_registry_groups_known_multi_actor_raid_fights():
    data_root = Path(__file__).resolve().parents[2] / "data"
    rows = {row.encounter_id: row for row in load_raid_encounter_identities(data_root)}

    assert rows["lylanar_turlassil"].member_ids == ("lylanar", "turlassil")
    assert rows["s_kinrai_vashai"].member_ids == ("s_kinrai", "vashai")
    assert rows["hunter_killers"].member_ids == (
        "hunter_killer_negatrix",
        "hunter_killer_positrox",
    )
    assert rows["jynorah_skorkhif"].member_ids == ("jynorah", "skorkhif")

    member_ids = {member for row in rows.values() for member in row.member_ids}
    assert "dro_m_athra" not in member_ids
    assert "dwarven_spider" not in member_ids
    assert "gryphon" not in member_ids
