from pathlib import Path

import pytest

from services.support_gear_reference_service import (
    SupportGearReference,
    SupportGearReferenceService,
)


def test_support_gear_reference_seeds_healer_and_tank_ideas(tmp_path: Path) -> None:
    service = SupportGearReferenceService(tmp_path / "foundrydock.db")

    healer = service.list_for_role("healer")
    tank = service.list_for_role("tank")

    assert healer
    assert tank
    assert any(row.set_name == "Powerful Assault" for row in healer)
    assert any(row.set_name == "Pillager's Profit" for row in healer)
    assert any(row.set_name == "Lucent Echoes" for row in tank)
    assert any(row.set_name == "Pearlescent Ward" for row in tank)


def test_support_gear_reference_persists_user_added_set(tmp_path: Path) -> None:
    database = tmp_path / "foundrydock.db"
    service = SupportGearReferenceService(database)
    created = service.create(
        role="healer",
        set_name="Test Support Set",
        coverage="Major Test",
        notes="Idea only",
    )

    reloaded = SupportGearReferenceService(database)
    rows = reloaded.list_for_role("healer")

    assert any(row.reference_id == created.reference_id for row in rows)
    assert next(row for row in rows if row.reference_id == created.reference_id).notes == "Idea only"


def test_support_gear_reference_allows_edit_and_delete(tmp_path: Path) -> None:
    service = SupportGearReferenceService(tmp_path / "foundrydock.db")
    created = service.create(
        role="tank",
        set_name="First Name",
        coverage="Armor support",
    )
    service.save(
        SupportGearReference(
            reference_id=created.reference_id,
            role="tank",
            set_name="Renamed Set",
            coverage="Major Vulnerability",
            notes="Changed idea",
            seeded=False,
        )
    )

    rows = service.list_for_role("tank")
    assert any(
        row.reference_id == created.reference_id
        and row.set_name == "Renamed Set"
        and row.coverage == "Major Vulnerability"
        for row in rows
    )

    service.delete(created.reference_id)
    assert all(
        row.reference_id != created.reference_id
        for row in service.list_for_role("tank")
    )


def test_support_gear_reference_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="role must be healer or tank"):
        SupportGearReference(
            reference_id="x",
            role="dd",
            set_name="Set",
            coverage="Effect",
        )


def test_support_gear_create_reuses_same_role_set_identity(tmp_path: Path) -> None:
    service = SupportGearReferenceService(tmp_path / "foundrydock.db")
    first = service.create(
        role="healer",
        set_name="Powerful Assault",
        coverage="Unique damage buff",
        notes="first",
    )
    second = service.create(
        role="healer",
        set_name="Powerful Assault",
        coverage="Unique Weapon / Spell Damage",
        notes="updated",
    )

    matches = [
        row
        for row in service.list_for_role("healer")
        if row.set_name == "Powerful Assault"
    ]
    assert first.reference_id == second.reference_id
    assert len(matches) == 1
    assert matches[0].notes == "updated"
