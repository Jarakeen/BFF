from models.build_model import PlayerBuild
from services.team_prescription import TeamPrescriptionScope
from services.team_prescription_generator import generate_prescribed_roster_from_saved_builds


def _trial_slots() -> tuple[str, ...]:
    return (
        "Main Tank",
        "Off Tank",
        "Healer 1",
        "Healer 2",
        "DD 1",
        "DD 2",
        "DD 3",
        "DD 4",
        "DD 5",
        "DD 6",
        "DD 7",
        "DD 8",
    )


def test_godslayer_prescription_anchors_necro_tank_and_warden_healer_by_role() -> None:
    healer = PlayerBuild(
        Name="Warden Healer",
        BuildName="GS Healer",
        EsoClass="Warden",
        Race="Breton",
        Role="Healer",
    )
    tank = PlayerBuild(
        Name="Necro Tank",
        BuildName="GS Tank",
        EsoClass="Necromancer",
        Race="Nord",
        Role="Tank",
    )

    prescription = generate_prescribed_roster_from_saved_builds(
        name="Bestest Godslayer Team",
        goal="Godslayer",
        slot_labels=_trial_slots(),
        builds=(healer, tank),
        scope=TeamPrescriptionScope(),
    )

    assert len(prescription.assignments) == 12
    assert prescription.goal == "Godslayer"

    main_tank = prescription.assignments[0]
    off_tank = prescription.assignments[1]
    healer_one = prescription.assignments[2]
    healer_two = prescription.assignments[3]

    assert main_tank.player_name == "Necro Tank"
    assert main_tank.source_build_name == "GS Tank"
    assert main_tank.prescribed_role == "Tank"
    assert off_tank.player_name is None

    assert healer_one.player_name == "Warden Healer"
    assert healer_one.source_build_name == "GS Healer"
    assert healer_one.prescribed_role == "Healer"
    assert healer_two.player_name is None

    assert sum(assignment.player_name is None for assignment in prescription.assignments) == 10
    assert len(prescription.unresolved) == 10


def test_open_prescribed_slots_do_not_invent_class_race_or_gear() -> None:
    prescription = generate_prescribed_roster_from_saved_builds(
        name="Sparse Trial Team",
        goal="Godslayer",
        slot_labels=("Main Tank", "Healer 1", "DD 1"),
        builds=(),
        scope=TeamPrescriptionScope(),
    )

    for assignment in prescription.assignments:
        assert assignment.player_name is None
        assert assignment.source_build_name is None
        assert assignment.changes == ()
        assert any("optimization evidence" in item for item in assignment.unresolved)


def test_prescription_generator_does_not_mutate_saved_builds() -> None:
    healer = PlayerBuild(
        Name="Warden Healer",
        BuildName="Existing Healer",
        EsoClass="Warden",
        Race="Breton",
        Role="Healer",
    )
    before = healer.to_dict()

    generate_prescribed_roster_from_saved_builds(
        name="No Mutation",
        goal="Godslayer",
        slot_labels=("Healer 1",),
        builds=(healer,),
        scope=TeamPrescriptionScope(),
    )

    assert healer.to_dict() == before


def test_prescription_generator_rejects_blank_slot_labels() -> None:
    try:
        generate_prescribed_roster_from_saved_builds(
            name="Bad Slots",
            goal="Godslayer",
            slot_labels=("Main Tank", ""),
            builds=(),
            scope=TeamPrescriptionScope(),
        )
    except ValueError as exc:
        assert "non-empty slot labels" in str(exc)
    else:
        raise AssertionError("blank slot label should be rejected")
