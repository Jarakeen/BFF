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
