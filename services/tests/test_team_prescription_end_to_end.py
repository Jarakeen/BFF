import json

from models.build_model import GearSlot, PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_promotion import promote_prescribed_slot_to_character_build
from services.team_prescription_template_sources import apply_team_template_sources
from ui.team_prescription_row_display_support import prescribed_recruit_row_values


def _write_complete_healer_template(tmp_path) -> None:
    build = PlayerBuild(
        BuildName="Published Brittle Warden",
        EsoClass="Warden",
        Race="Breton",
        Role="Healer",
        Mundus="The Ritual",
        FrontBarWeapon=GearSlot(Set="Serpent's Disdain"),
        BackBarWeapon=GearSlot(Set="Pillager's Profit"),
        FrontBarSkills=[
            "Combat Prayer",
            "Energy Orb",
            "Budding Seeds",
            "Frost Cloak",
            "Radiating Regeneration",
            "Enchanted Forest",
        ],
    )
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_version": "u50-integration",
                "game_update": "U50",
                "templates": [
                    {
                        "template_id": "published:u50:brittle-warden",
                        "name": "Published Brittle Warden",
                        "source_name": "Curated Integration Source",
                        "source_url": "https://example.invalid/brittle-warden",
                        "retrieved_at": "2026-09-04",
                        "base_score": 200.0,
                        "complete_build": True,
                        "build": build.to_dict(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _hybrid_roster() -> PrescribedRoster:
    return PrescribedRoster(
        name="Gryphon Heart Prescribed Roster",
        goal="Gryphon Heart",
        scope=TeamPrescriptionScope(
            dimensions=(
                PrescriptionDimension.CLASS,
                PrescriptionDimension.RACE,
                PrescriptionDimension.BUILD,
                PrescriptionDimension.GEAR,
                PrescriptionDimension.SKILLS,
                PrescriptionDimension.MUNDUS,
            )
        ),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Main Tank",
                player_name="Susan",
                source_build_name="DK Tank",
                prescribed_role="Tank",
            ),
            PrescribedRosterAssignment(
                slot_name="Healer 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="Healer",
                unresolved=("Healer 1: recruit a compatible healer",),
            ),
        ),
        unresolved=("Healer 1: recruit a compatible healer",),
    )


def _character_catalog(tmp_path) -> BuildCatalogService:
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


def test_hybrid_open_chair_can_be_prescribed_displayed_and_promoted_without_overwrite(tmp_path) -> None:
    _write_complete_healer_template(tmp_path)
    original = _hybrid_roster()

    result = apply_team_template_sources(
        roster=original,
        goal="Gryphon Heart",
        data_dir=tmp_path,
    )

    assert result.applied_count == 1
    assert result.final_roster.assignments[0].player_name == "Susan"
    healer = result.final_roster.assignments[1]
    assert healer.player_name is None
    assert healer.source_build_name == "Published Brittle Warden"
    assert healer.prescribed_build is not None
    assert healer.prescribed_build.FrontBarWeapon.Set == "Serpent's Disdain"
    assert healer.prescribed_build.BackBarWeapon.Set == "Pillager's Profit"
    assert not result.final_roster.unresolved

    row = prescribed_recruit_row_values(healer)
    assert row is not None
    assert row[0] == "Warden"
    assert row[1] == "Published Brittle Warden"
    assert "Serpent's Disdain" in row[2]
    assert row[3] == "PRESCRIBED"

    catalog = _character_catalog(tmp_path)
    promoted = promote_prescribed_slot_to_character_build(
        catalog_service=catalog,
        roster=result.final_roster,
        slot_name="Healer 1",
        character_id="magrat",
        build_name="GH Healer",
    )

    assert promoted.build_name == "GH Healer"
    builds = catalog.builds_for_character("magrat")
    assert {entry["name"] for entry in builds} == {"DF Healer", "GH Healer"}
    df = next(entry for entry in builds if entry["name"] == "DF Healer")
    gh = next(entry for entry in builds if entry["name"] == "GH Healer")
    assert df["payload"]["FrontBarWeapon"]["Set"] == "Spell Power Cure"
    assert gh["payload"]["FrontBarWeapon"]["Set"] == "Serpent's Disdain"
    assert gh["payload"]["BackBarWeapon"]["Set"] == "Pillager's Profit"
    assert gh["payload"]["BuildName"] == "GH Healer"
