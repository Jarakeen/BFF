from __future__ import annotations

from types import SimpleNamespace

from ui.roster_import_sparse_alternate_support import (
    _merge_inherited,
    _split_multi_family_members,
)


def test_blank_alternate_values_inherit_complete_base_setup() -> None:
    base = {
        "AttributeMagicka": 64,
        "Food": "Clockwork Citrus Filet",
        "FrontBarSkills": ["Combat Prayer", "Energy Orb", "Illustrious Healing", "Radiating Regen", "Budding Seeds", "Bear"],
        "Armor": {"Chest": {"Set": "Spell Power Cure", "Trait": "Divines"}},
    }
    alternate = {
        "FrontBarSkills": ["", "", "", "", "", ""],
        "Armor": {"Chest": {"Set": "Pillager's Profit", "Trait": ""}},
    }

    merged = _merge_inherited(base, alternate)

    assert merged["AttributeMagicka"] == 64
    assert merged["Food"] == "Clockwork Citrus Filet"
    assert merged["FrontBarSkills"] == base["FrontBarSkills"]
    assert merged["Armor"]["Chest"]["Set"] == "Pillager's Profit"
    assert merged["Armor"]["Chest"]["Trait"] == "Divines"


def test_one_player_with_two_class_build_families_becomes_two_import_rows() -> None:
    den = SimpleNamespace(eso_class="Warden", role="Damage Dealer", build_name="Brittle Den - Trash", payload={})
    arc = SimpleNamespace(eso_class="Arcanist", role="Damage Dealer", build_name="Pure Arc - Trash", payload={})
    member = SimpleNamespace(
        gamertag="Twizted",
        character_name="Twizted Den DD",
        eso_class="Warden",
        primary_role="Damage Dealer",
        builds=[den, arc],
    )
    plan = SimpleNamespace(members=[member])

    _split_multi_family_members(plan)

    assert len(plan.members) == 2
    assert {row.eso_class for row in plan.members} == {"Warden", "Arcanist"}
    assert next(row for row in plan.members if row.eso_class == "Warden").character_name == "Twizted Den DD"
    assert next(row for row in plan.members if row.eso_class == "Arcanist").character_name == ""
