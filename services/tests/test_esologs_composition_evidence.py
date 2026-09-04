import json

from models.top_team_model import TopTeamPlayer, TopTeamResult
from services.esologs_composition_evidence import EsoLogsCompositionEvidenceService


def _result(*, encounter: str, report: str, healer_class: str) -> TopTeamResult:
    return TopTeamResult(
        TrialName="Sunspire",
        EncounterName=encounter,
        ReportCode=report,
        FightId=7,
        Players=[
            TopTeamPlayer(Name="MT", Role="tank", ClassName="Dragonknight", GearSets=["Pearlescent Ward"]),
            TopTeamPlayer(Name="OT", Role="tank", ClassName="Sorcerer", GearSets=["Turning Tide"]),
            TopTeamPlayer(
                Name="GH",
                Role="healer",
                ClassName=healer_class,
                GearSets=["Spell Power Cure", "Pillager's Profit"],
                Abilities=["Combat Prayer", "Energy Orb"],
            ),
            TopTeamPlayer(Name="H2", Role="healer", ClassName="Arcanist"),
            *[
                TopTeamPlayer(Name=f"DD {index}", Role="dps", ClassName="Dragonknight" if index <= 2 else "Sorcerer")
                for index in range(1, 9)
            ],
        ],
    )


def test_aggregate_builds_deterministic_two_two_eight_chairs_from_observed_teams() -> None:
    service = EsoLogsCompositionEvidenceService()

    evidence = service.aggregate(
        (
            _result(encounter="Yolnahkriin", report="AAA", healer_class="Warden"),
            _result(encounter="Nahviintaas", report="BBB", healer_class="Warden"),
        )
    )

    assert evidence.trial_name == "Sunspire"
    assert evidence.sample_count == 2
    assert evidence.encounter_names == ("Yolnahkriin", "Nahviintaas")
    assert evidence.report_fights == ("AAA#7", "BBB#7")
    assert len(evidence.slots) == 12
    assert [slot.slot_name for slot in evidence.slots[:4]] == [
        "Main Tank",
        "Off Tank",
        "Healer 1",
        "Healer 2",
    ]
    assert evidence.slot("Main Tank").preferred_class == "Dragonknight"
    assert evidence.slot("Healer 1").preferred_class == "Warden"
    assert evidence.slot("Healer 1").confidence == 1.0


def test_aggregate_keeps_class_alternatives_and_observed_setup_frequency() -> None:
    service = EsoLogsCompositionEvidenceService()

    evidence = service.aggregate(
        (
            _result(encounter="Yolnahkriin", report="AAA", healer_class="Warden"),
            _result(encounter="Nahviintaas", report="BBB", healer_class="Arcanist"),
            _result(encounter="Lokkestiiz", report="CCC", healer_class="Warden"),
        )
    )

    healer = evidence.slot("Healer 1")
    assert healer.preferred_class == "Warden"
    assert healer.alternative_classes == ("Arcanist",)
    assert healer.class_counts == (("Warden", 2), ("Arcanist", 1))
    assert healer.observed_gear_sets[:2] == (
        ("Pillager's Profit", 3),
        ("Spell Power Cure", 3),
    )
    assert healer.observed_abilities == (("Combat Prayer", 3), ("Energy Orb", 3))


def test_load_snapshots_accepts_external_grabber_interchange_aliases(tmp_path) -> None:
    path = tmp_path / "grabber.json"
    path.write_text(
        json.dumps(
            {
                "snapshots": [
                    {
                        "trial_name": "Dreadsail Reef",
                        "encounter_name": "Taleria",
                        "report_code": "XYZ",
                        "fight_id": 3,
                        "players": [
                            {
                                "name": "ObservedHealer",
                                "role": "healer",
                                "class_name": "Warden",
                                "gear_sets": ["Serpent's Disdain"],
                                "abilities": ["Combat Prayer"],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    service = EsoLogsCompositionEvidenceService()
    results = service.load_snapshots(path)

    assert len(results) == 1
    assert results[0].TrialName == "Dreadsail Reef"
    assert results[0].EncounterName == "Taleria"
    assert results[0].ReportCode == "XYZ"
    assert results[0].FightId == 3
    assert results[0].Players[0].ClassName == "Warden"
    assert results[0].Players[0].GearSets == ["Serpent's Disdain"]
