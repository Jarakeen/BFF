import json

import pytest

from models.build_model import GearSlot, PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    TeamPrescriptionScope,
)
from services.team_prescription_candidate_source import PrescribedOpenSlotCandidate
from services.team_prescription_promotion import (
    promote_prescribed_slot_to_character_build,
)


def _catalog(tmp_path) -> BuildCatalogService:
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    catalog["characters"] = [
        {
            "character_id": "magrat",
            "name": "Magrat",
            "gamertag": "Jarakeen",
            "eso_class": "Warden",
            "race": "Breton",
            "role": "Healer",
        }
    ]
    service.save(catalog)
    service.upsert_build(
        character_id="magrat",
        build_name="DF Healer",
        payload=PlayerBuild(
            Name="Magrat",
            Gamertag="Jarakeen",
            BuildName="DF Healer",
            EsoClass="Warden",
            Race="Breton",
            Role="Healer",
            FrontBarWeapon=GearSlot(Set="Spell Power Cure"),
        ).to_dict(),
    )
    return service


def _prescription() -> PrescribedRoster:
    build = PlayerBuild(
        BuildName="Brittle Warden Template",
        EsoClass="Warden",
        Race="Breton",
        Role="Healer",
        FrontBarWeapon=GearSlot(Set="Serpent's Disdain"),
    )
    snapshot = PrescribedOpenSlotCandidate.from_build(
        candidate_id="btv:u50:brittle-warden",
        candidate_build=build,
        candidate_source="BTV Tools U50",
    ).candidate_build_json
    return PrescribedRoster(
        name="Generated Gryphon Heart Team",
        goal="Gryphon Heart",
        scope=TeamPrescriptionScope(),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Healer 1",
                player_name=None,
                source_build_name="Brittle Warden Template",
                prescribed_role="Healer",
                prescribed_build_json=snapshot,
            ),
        ),
    )


def test_promoting_team_slot_creates_new_character_build_without_overwriting_old(tmp_path) -> None:
    service = _catalog(tmp_path)

    result = promote_prescribed_slot_to_character_build(
        catalog_service=service,
        roster=_prescription(),
        slot_name="Healer 1",
        character_id="magrat",
        build_name="GH Healer",
    )

    assert result.build_name == "GH Healer"
    builds = service.builds_for_character("magrat")
    assert {build["name"] for build in builds} == {"DF Healer", "GH Healer"}
    gh = next(build for build in builds if build["name"] == "GH Healer")
    assert gh["payload"]["Name"] == "Magrat"
    assert gh["payload"]["FrontBarWeapon"]["Set"] == "Serpent's Disdain"
    df = next(build for build in builds if build["name"] == "DF Healer")
    assert df["payload"]["FrontBarWeapon"]["Set"] == "Spell Power Cure"


def test_promotion_refuses_implicit_build_replacement(tmp_path) -> None:
    service = _catalog(tmp_path)
    promote_prescribed_slot_to_character_build(
        catalog_service=service,
        roster=_prescription(),
        slot_name="Healer 1",
        character_id="magrat",
        build_name="GH Healer",
    )

    with pytest.raises(ValueError, match="explicit replacement permission"):
        promote_prescribed_slot_to_character_build(
            catalog_service=service,
            roster=_prescription(),
            slot_name="Healer 1",
            character_id="magrat",
            build_name="GH Healer",
        )


def test_promotion_refuses_wrong_character_class(tmp_path) -> None:
    service = _catalog(tmp_path)
    catalog = service.load()
    catalog["characters"][0]["eso_class"] = "Arcanist"
    service.save(catalog)

    with pytest.raises(ValueError, match="incompatible"):
        promote_prescribed_slot_to_character_build(
            catalog_service=service,
            roster=_prescription(),
            slot_name="Healer 1",
            character_id="magrat",
            build_name="GH Healer",
        )


def test_assignment_rejects_corrupt_prescribed_build_snapshot() -> None:
    with pytest.raises(ValueError, match="invalid build snapshot"):
        PrescribedRosterAssignment(
            slot_name="Healer 1",
            player_name=None,
            source_build_name="Broken",
            prescribed_role="Healer",
            prescribed_build_json=json.dumps(["not", "a", "build"]),
        )
