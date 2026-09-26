from __future__ import annotations

import pytest

from models.roster_model import RosterMember
from models.team_schedule import TeamSchedule, TeamScheduleSlot
from services.eso_database import EsoDatabase
from services.roster_service import RosterService


def test_personnel_pydantic_gate_rejects_invalid_role_before_write(tmp_path) -> None:
    service = RosterService(EsoDatabase(tmp_path / "foundrydock.db"))

    with pytest.raises(ValueError, match="unsupported Personnel role"):
        service.create_member(RosterMember(PlayerName="Aces", PrimaryRole="Wizard"))

    assert service.list_members(include_archived=True) == []


def test_personnel_pydantic_gate_rejects_invalid_class_before_write(tmp_path) -> None:
    service = RosterService(EsoDatabase(tmp_path / "foundrydock.db"))

    with pytest.raises(ValueError, match="unsupported ESO class"):
        service.create_member(RosterMember(PlayerName="Aces", EsoClass="Bard"))

    assert service.list_members(include_archived=True) == []


def test_team_schedule_pydantic_gate_rejects_duplicate_days_before_write(tmp_path) -> None:
    service = RosterService(EsoDatabase(tmp_path / "foundrydock.db"))
    schedule = TeamSchedule(
        TeamName="Performance Mode",
        Slots=(
            TeamScheduleSlot(Day="Monday", StartTime="21:00", EndTime="23:00"),
            TeamScheduleSlot(Day="monday", StartTime="21:00", EndTime="23:00"),
        ),
    )

    with pytest.raises(ValueError, match="duplicate raid days"):
        service.set_team_schedule(schedule)

    assert service.get_team_schedule("Performance Mode") is None


def test_status_write_uses_personnel_pydantic_gate(tmp_path) -> None:
    service = RosterService(EsoDatabase(tmp_path / "foundrydock.db"))
    member_id = service.create_member(RosterMember(PlayerName="Aces"))

    with pytest.raises(ValueError, match="unsupported Personnel status"):
        service.set_member_status(member_id, "Vanished Into The Void")

    assert service.get_member(member_id).Status == "Active"


def test_assignment_write_rejects_oversized_value_before_mutation(tmp_path) -> None:
    service = RosterService(EsoDatabase(tmp_path / "foundrydock.db"))
    member_id = service.create_member(RosterMember(PlayerName="Aces"))

    with pytest.raises(ValueError, match="Pydantic validation"):
        service.set_member_assignment_field(member_id, "notes", "x" * 12001)

    assignments = service.get_member_assignment(member_id)
    assert assignments["notes"] == ""


def test_team_identity_write_rejects_oversized_name_before_mutation(tmp_path) -> None:
    service = RosterService(EsoDatabase(tmp_path / "foundrydock.db"))

    with pytest.raises(ValueError, match="Pydantic validation"):
        service.ensure_team_name("x" * 241)

    assert service.list_team_names() == []
