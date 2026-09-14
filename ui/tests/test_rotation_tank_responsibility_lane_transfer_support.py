from types import SimpleNamespace

from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterResponsibilityBindingService,
)
from ui.rotation_tank_provider_scope_transfer_support import (
    _bind_encounter_responsibilities,
)


class _CapabilityService:
    def audit_build(self, build):
        return SimpleNamespace(
            character_id=f"id:{build.Name.casefold().replace(' ', '-')}",
            character_name=build.Name,
            build_name=build.BuildName,
        )


class _UtilityService:
    def provider_sources_for(self, *, build, capability_type):
        if capability_type == "taunt" and getattr(build, "HasTaunt", False):
            return SimpleNamespace(sources=(object(),), unresolved=())
        return SimpleNamespace(sources=(), unresolved=())


class _ProviderScopeService:
    capability_service = _CapabilityService()
    utility_capability_service = _UtilityService()


def _build(name, build_name, *, taunt=True):
    return SimpleNamespace(
        Name=name,
        BuildName=build_name,
        Role="Tank",
        HasTaunt=taunt,
    )


def _assignment(build, slot_name):
    return SimpleNamespace(
        slot_name=slot_name,
        player_name=build.Name,
        source_build_name=build.BuildName,
    )


def _optimization_page(main_tank, off_tank):
    return SimpleNamespace(
        roster=SimpleNamespace(Members=[main_tank, off_tank]),
        current_prescription=SimpleNamespace(
            assignments=(
                _assignment(main_tank, "Main Tank"),
                _assignment(off_tank, "Off Tank"),
            )
        ),
    )


def test_xalvakka_transfer_binds_main_and_off_tank_from_authoritative_prescription():
    main = _build("Tank A", "MT")
    off = _build("Tank B", "OT")

    binding, unresolved = _bind_encounter_responsibilities(
        encounter_id="xalvakka",
        optimization_page=_optimization_page(main, off),
        provider_scope_service=_ProviderScopeService(),
        binding_service=RaidTankEncounterResponsibilityBindingService(),
    )

    assert unresolved == ()
    assert binding is not None
    assert binding.resolved is True
    assert [(row.lane_id, row.member_id) for row in binding.assignments] == [
        ("boss_holder", "id:tank-a"),
        ("add_handler", "id:tank-b"),
    ]
    assert [
        row.responsibility.responsibility_id
        for row in binding.for_member("id:tank-b")
    ] == [
        "pack_encounter_adds",
        "iron_atronach_opening_position",
        "daedroth_facing",
    ]


def test_xalvakka_transfer_fails_closed_when_off_tank_lacks_taunt():
    main = _build("Tank A", "MT")
    off = _build("Tank B", "OT", taunt=False)

    binding, unresolved = _bind_encounter_responsibilities(
        encounter_id="xalvakka",
        optimization_page=_optimization_page(main, off),
        provider_scope_service=_ProviderScopeService(),
        binding_service=RaidTankEncounterResponsibilityBindingService(),
    )

    assert binding is not None
    assert binding.resolved is False
    assert any("lacks required canonical capability evidence: taunt" in row for row in unresolved)


def test_unreviewed_encounter_has_no_lane_binding_requirement():
    main = _build("Tank A", "MT")
    off = _build("Tank B", "OT")

    binding, unresolved = _bind_encounter_responsibilities(
        encounter_id="taleria_hm",
        optimization_page=_optimization_page(main, off),
        provider_scope_service=_ProviderScopeService(),
        binding_service=RaidTankEncounterResponsibilityBindingService(),
    )

    assert binding is None
    assert unresolved == ()
