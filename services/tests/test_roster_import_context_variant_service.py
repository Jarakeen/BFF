from __future__ import annotations

from types import SimpleNamespace

from models.build_model import PlayerBuild
from services.build_context_variant_service import resolve_build_context
from services.roster_import_context_variant_service import consolidate_member_builds


def _candidate(name: str, *, chest_set: str, skill: str = ""):
    payload = PlayerBuild(
        BuildName=name,
        EsoClass="Warden",
        Role="Healer",
    ).to_dict()
    payload["Armor"]["Chest"]["Set"] = chest_set
    payload["FrontBarSkills"][0] = skill
    return SimpleNamespace(build_name=name, payload=payload)


def test_generic_boss_loadout_becomes_team_boss_wildcard(tmp_path) -> None:
    data = tmp_path
    (data / "raid_encounter_identity.json").write_text(
        '{"schema_version":1,"encounters":[]}', encoding="utf-8"
    )
    candidates = [
        _candidate("Pure Den - Trash", chest_set="Spell Power Cure", skill="Energy Orb"),
        _candidate("Bosses", chest_set="Pillager's Profit", skill="Combat Prayer"),
    ]

    prepared, report = consolidate_member_builds(
        candidates,
        team_name="Swine & Punishment",
        data_root=data,
    )

    assert len(prepared) == 1
    assert report.folded_contexts == ("*",)
    build = PlayerBuild.from_dict(prepared[0].payload)
    assert build.Armor["Chest"]["Set"] == "Spell Power Cure"

    trash = resolve_build_context(build, team_name="Swine & Punishment", boss_name="")
    assert trash.Armor["Chest"]["Set"] == "Spell Power Cure"

    boss = resolve_build_context(build, team_name="Swine & Punishment", boss_name="Reef Guardian")
    assert boss.Armor["Chest"]["Set"] == "Pillager's Profit"
    assert boss.FrontBarSkills[0] == "Combat Prayer"


def test_dreadsail_names_and_ordinals_resolve_to_reviewed_bosses(tmp_path) -> None:
    (tmp_path / "raid_encounter_identity.json").write_text(
        """{
          "schema_version": 1,
          "encounters": [
            {"content_id":"dreadsail_reef","content_name":"Dreadsail Reef","encounter_id":"lylanar_turlassil","display_name":"Lylanar and Turlassil","member_ids":["lylanar","turlassil"]},
            {"content_id":"dreadsail_reef","content_name":"Dreadsail Reef","encounter_id":"reef_guardian","display_name":"Reef Guardian","member_ids":["reef_guardian"]},
            {"content_id":"dreadsail_reef","content_name":"Dreadsail Reef","encounter_id":"tideborn_taleria","display_name":"Tideborn Taleria","member_ids":["tideborn_taleria"]}
          ]
        }""",
        encoding="utf-8",
    )
    candidates = [
        _candidate("Trash - Pure Sorc", chest_set="Base"),
        _candidate("Twins", chest_set="Twins Set"),
        _candidate("Boss 2 Portal", chest_set="Portal Set"),
        _candidate("Taleria", chest_set="Taleria Set"),
    ]

    prepared, report = consolidate_member_builds(
        candidates,
        team_name="Swine & Punishment",
        data_root=tmp_path,
    )

    assert len(prepared) == 1
    assert report.folded_contexts == (
        "Lylanar and Turlassil",
        "Reef Guardian",
        "Tideborn Taleria",
    )
    build = PlayerBuild.from_dict(prepared[0].payload)
    assert resolve_build_context(
        build,
        team_name="Swine & Punishment",
        boss_name="Lylanar and Turlassil",
    ).Armor["Chest"]["Set"] == "Twins Set"
    assert resolve_build_context(
        build,
        team_name="Swine & Punishment",
        boss_name="Reef Guardian",
    ).Armor["Chest"]["Set"] == "Portal Set"
    assert resolve_build_context(
        build,
        team_name="Swine & Punishment",
        boss_name="Tideborn Taleria",
    ).Armor["Chest"]["Set"] == "Taleria Set"


def test_lossy_alternate_stays_a_separate_build(tmp_path) -> None:
    (tmp_path / "raid_encounter_identity.json").write_text(
        '{"schema_version":1,"encounters":[]}', encoding="utf-8"
    )
    base = _candidate("Trash", chest_set="Base", skill="Energy Orb")
    alt = _candidate("Bosses", chest_set="Boss", skill="")

    prepared, report = consolidate_member_builds(
        [base, alt],
        team_name="Team",
        data_root=tmp_path,
    )

    assert len(prepared) == 2
    assert not report.folded_contexts
    assert any("cannot safely clear" in warning for warning in report.warnings)
