from tools.audit_phase13_staff_heavy_actor_modifier_evidence import (
    _class_name,
    _gear_set_names,
    _raw_actor_by_id,
    _selected_combatant_scalars,
    _talent_names,
)


def _actor():
    return {
        "id": 7,
        "name": "Anonymous 7",
        "type": "Warden",
        "combatantInfo": {
            "gear": [
                {"setName": "Spell Power Cure", "slot": "Head", "id": 1},
                {"set": {"name": "Pillager's Profit"}, "slot": "Chest", "id": 2},
                {"setName": "Spell Power Cure", "slot": "Hands", "id": 3},
            ],
            "talents": [
                {"name": "Cycle of Life"},
                {"ability": {"name": "Combat Prayer"}},
                {"name": "Cycle of Life"},
            ],
            "championPoints": 2694,
            "spec": "healer",
        },
    }


def test_raw_actor_by_id_unwraps_grouped_player_details():
    details = {
        "data": {
            "playerDetails": {
                "healers": [_actor()],
                "tanks": [],
                "dps": [],
            }
        }
    }

    actors = _raw_actor_by_id(details)

    assert actors[7][0] == "healer"
    assert actors[7][1]["name"] == "Anonymous 7"


def test_actor_modifier_helpers_preserve_observational_build_evidence():
    actor = _actor()

    assert _class_name(actor) == "Warden"
    assert _gear_set_names(actor) == ("Spell Power Cure", "Pillager's Profit")
    assert _talent_names(actor) == ("Cycle of Life", "Combat Prayer")
    assert _selected_combatant_scalars(actor) == {
        "championPoints": 2694,
        "spec": "healer",
    }
