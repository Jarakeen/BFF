from __future__ import annotations

from services.phase10_closeout_audit import audit_phase10_roster_inventory
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _audit(character: str, build: str, identity: str) -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name=character,
        build_name=build,
        character_id=identity,
        resolved_effects=(),
        unresolved=(),
    )


def test_closeout_inventory_excludes_blank_and_template_builds():
    inventory = audit_phase10_roster_inventory(
        (
            _audit("Magrat", "DF Healer", "magrat"),
            _audit("", "", ""),
            _audit("YOUR TANK BUILD", "YOUR TANK BUILD", "tank-template"),
        )
    )

    assert inventory.real_build_count == 1
    assert inventory.unique_member_ids == ("magrat",)
    assert inventory.unique_member_count == 1
    assert inventory.has_multi_member_real_roster is False
    assert len(inventory.template_or_blank_builds) == 2


def test_closeout_inventory_detects_multi_member_real_roster():
    inventory = audit_phase10_roster_inventory(
        (
            _audit("Tank", "Oax Tank", "tank"),
            _audit("Healer", "Oax Healer", "healer"),
            _audit("DD", "Oax DD", "dd"),
        )
    )

    assert inventory.unique_member_count == 3
    assert inventory.has_multi_member_real_roster is True
    assert inventory.duplicate_member_ids == ()


def test_closeout_inventory_reports_multiple_builds_for_same_character():
    inventory = audit_phase10_roster_inventory(
        (
            _audit("Magrat", "DF Healer", "magrat"),
            _audit("Magrat", "Oax Healer", "magrat"),
            _audit("Tank", "Oax Tank", "tank"),
        )
    )

    assert inventory.has_multi_member_real_roster is True
    assert inventory.duplicate_member_ids == ("magrat",)
    assert inventory.has_ambiguous_member_builds is True
