from services.encounter_requirement_evaluation import RequirementSemantics
from services.raid_tank_responsibility_encounter_adapter import (
    RaidTankResponsibilityEncounterAdapter,
)
from services.raid_tank_responsibility_profile import (
    DEFAULT_RAID_TANK_RESPONSIBILITY_PROFILE,
)


def test_default_tank_responsibility_projects_exact_boss_taunt_requirement():
    adapter = RaidTankResponsibilityEncounterAdapter(
        DEFAULT_RAID_TANK_RESPONSIBILITY_PROFILE
    )

    rows = adapter.requirements("xalvakka")

    assert len(rows) == 1
    assert rows[0].requirement_id == "xalvakka:tank:boss_taunt"
    assert rows[0].requirement_type == "taunt"
    assert rows[0].interpretation_status == "configured_raid_tank_responsibility"
    assert adapter.requirement_semantics() == {
        "taunt": RequirementSemantics.PROVIDER_CAPABILITY
    }
    assert adapter.required_provider_counts("xalvakka") == {
        "xalvakka:tank:boss_taunt": 1
    }
    assert adapter.capability_types == ("taunt",)
