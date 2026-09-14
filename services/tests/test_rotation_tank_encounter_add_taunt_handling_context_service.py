from services.raid_tank_encounter_responsibility_binding_service import RaidTankEncounterBoundResponsibility
from services.raid_tank_encounter_responsibility_lane_service import RaidTankEncounterResponsibility
from services.rotation_tank_encounter_add_taunt_handling_context_service import RotationTankEncounterAddTauntHandlingContextService


class _Actor:
    def __init__(self, name, handling, ranking=True):
        self.actor_name = name
        self.handling_class = handling
        self.ranking_context = ranking
        self.interpretation = f"{name} reviewed"


class _Plan:
    actors = (
        _Actor("Iron Atronach", "strong_taunt_maintenance_target"),
        _Actor("Daedroth", "selective_contextual_taunt_target"),
    )


class _Service:
    def reviewed_for(self, encounter_id):
        assert encounter_id == "xalvakka"
        return _Plan()


def _bound(target):
    return RaidTankEncounterBoundResponsibility(
        encounter_id="xalvakka",
        lane_id="add_handler",
        member_id="tank-b",
        responsibility=RaidTankEncounterResponsibility(
            responsibility_id=f"handle_{target}",
            target_key=target,
            action_type="handle",
            required_capability_type="taunt",
            source="fixture",
        ),
    )


def test_generic_add_responsibility_projects_actor_specific_handling_context():
    rows = RotationTankEncounterAddTauntHandlingContextService(_Service()).for_responsibilities(
        encounter_id="xalvakka",
        responsibilities=(_bound("encounter_adds"),),
    )
    assert [(row.actor_name, row.handling_class) for row in rows] == [
        ("Iron Atronach", "strong_taunt_maintenance_target"),
        ("Daedroth", "selective_contextual_taunt_target"),
    ]


def test_specific_actor_responsibility_does_not_leak_other_actor_context():
    rows = RotationTankEncounterAddTauntHandlingContextService(_Service()).for_responsibilities(
        encounter_id="xalvakka",
        responsibilities=(_bound("iron_atronach"),),
    )
    assert [row.actor_name for row in rows] == ["Iron Atronach"]
