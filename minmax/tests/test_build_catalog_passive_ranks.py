from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from services.build_catalog_service import BuildCatalogService, SCHEMA_VERSION


def _service_with_character(tmp_path: Path) -> tuple[BuildCatalogService, str]:
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    catalog["characters"].append(
        {
            "character_id": "character_alice",
            "name": "Alice",
            "gamertag": "AliceGT",
        }
    )
    service.save(catalog)
    return service, "character_alice"


def test_character_defaults_to_no_passive_ranks(tmp_path: Path) -> None:
    service, character_id = _service_with_character(tmp_path)

    character = service.get_character(character_id)

    assert character is not None
    assert character["passive_ranks"] == {}
    assert service.get_passive_rank(character_id, "Medicinal Use") == 0
    assert service.load()["schema_version"] == SCHEMA_VERSION == 3


def test_set_passive_rank_is_character_scoped_and_case_insensitive(tmp_path: Path) -> None:
    service, character_id = _service_with_character(tmp_path)

    updated = service.set_passive_rank(
        character_id=character_id,
        passive_name="  Medicinal   Use ",
        rank=3,
    )

    assert updated is not None
    assert updated["passive_ranks"] == {"Medicinal Use": 3}
    assert service.get_passive_rank(character_id, "medicinal use") == 3

    updated = service.set_passive_rank(
        character_id=character_id,
        passive_name="MEDICINAL USE",
        rank=2,
    )

    assert updated is not None
    assert updated["passive_ranks"] == {"MEDICINAL USE": 2}
    assert service.get_passive_rank(character_id, "Medicinal Use") == 2


def test_rank_zero_removes_persisted_passive(tmp_path: Path) -> None:
    service, character_id = _service_with_character(tmp_path)
    service.set_passive_rank(
        character_id=character_id,
        passive_name="Medicinal Use",
        rank=3,
    )

    updated = service.set_passive_rank(
        character_id=character_id,
        passive_name="medicinal use",
        rank=0,
    )

    assert updated is not None
    assert updated["passive_ranks"] == {}
    assert service.get_passive_rank(character_id, "Medicinal Use") == 0


def test_passive_rank_update_does_not_modify_build_payload(tmp_path: Path) -> None:
    service, character_id = _service_with_character(tmp_path)
    build = service.upsert_build(
        character_id=character_id,
        build_name="Healer",
        payload={"BuildName": "Healer", "Potion": "spell power"},
    )

    service.set_passive_rank(
        character_id=character_id,
        passive_name="Medicinal Use",
        rank=3,
    )

    assert service.get_build(build["build_id"])["payload"] == {
        "BuildName": "Healer",
        "Potion": "spell power",
    }


def test_legacy_resync_preserves_character_passive_ranks(tmp_path: Path) -> None:
    service = BuildCatalogService(tmp_path / "characters.json")
    initial = service.import_legacy_roster(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Alice",
                    Gamertag="AliceGT",
                    BuildName="Healer",
                    EsoClass="Warden",
                )
            ]
        )
    )
    service.save(initial)
    character_id = initial["characters"][0]["character_id"]
    service.set_passive_rank(
        character_id=character_id,
        passive_name="Medicinal Use",
        rank=3,
    )

    resynced = service.import_legacy_roster(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Alice",
                    Gamertag="AliceGT",
                    BuildName="Healer",
                    EsoClass="Warden",
                    Mundus="The Ritual",
                )
            ]
        )
    )

    assert resynced["characters"][0]["character_id"] == character_id
    assert resynced["characters"][0]["passive_ranks"] == {"Medicinal Use": 3}


def test_invalid_passive_rank_fails_closed(tmp_path: Path) -> None:
    service, character_id = _service_with_character(tmp_path)

    for value in (-1, "not-a-rank"):
        try:
            service.set_passive_rank(
                character_id=character_id,
                passive_name="Medicinal Use",
                rank=value,  # type: ignore[arg-type]
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid passive rank should fail: {value!r}")
