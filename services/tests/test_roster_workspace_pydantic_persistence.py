from __future__ import annotations

from pathlib import Path

import pytest

from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from services.roster_workspace_state_service import (
    MemberAvailability,
    RecruitmentCandidate,
    RosterWorkspaceStateService,
)


def _service(tmp_path: Path) -> tuple[RosterWorkspaceStateService, int]:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    member_id = roster.create_member(
        RosterMember(PlayerName="Jarakeen", CharacterName="Magrat", Status="Active")
    )
    return RosterWorkspaceStateService(database), member_id


def test_availability_round_trips_exactly(tmp_path: Path) -> None:
    service, member_id = _service(tmp_path)
    expected = MemberAvailability(
        roster_member_id=member_id,
        monday="available",
        wednesday="late",
        preferred_times="9-11 PM EST",
        notes="Core nights",
    ).normalized()

    service.set_availability(expected)

    assert service.availability_for(member_id) == expected


def test_invalid_availability_is_rejected_before_mutation(tmp_path: Path) -> None:
    service, member_id = _service(tmp_path)
    service.set_availability(MemberAvailability(roster_member_id=member_id, notes="safe"))

    with pytest.raises(ValueError):
        service.set_availability(
            MemberAvailability(roster_member_id=member_id, notes="x" * 8001)
        )

    assert service.availability_for(member_id).notes == "safe"


def test_recruit_create_update_and_missing_update_are_fail_closed(tmp_path: Path) -> None:
    service, _member_id = _service(tmp_path)
    candidate_id = service.save_recruit(
        RecruitmentCandidate(player_name="Candidate", desired_role="DD", status="trial")
    )
    assert candidate_id > 0
    service.save_recruit(
        RecruitmentCandidate(
            id=candidate_id, player_name="Candidate", desired_role="Healer", status="review"
        )
    )
    saved = service.list_recruits(include_archived=True)
    assert len(saved) == 1
    assert saved[0].desired_role == "Healer"
    assert saved[0].status == "review"

    with pytest.raises(ValueError, match="does not exist"):
        service.save_recruit(
            RecruitmentCandidate(id=999999, player_name="Ghost", status="new")
        )
    assert len(service.list_recruits(include_archived=True)) == 1


def test_recruit_status_requires_existing_candidate(tmp_path: Path) -> None:
    service, _member_id = _service(tmp_path)

    with pytest.raises(ValueError, match="does not exist"):
        service.set_recruit_status(999999, "trial")


def test_archive_round_trips_structured_payload(tmp_path: Path) -> None:
    service, _member_id = _service(tmp_path)
    archive_id = service.archive(
        entity_type="team",
        entity_key="performance-mode",
        display_name="Performance Mode",
        reason="test",
        payload={"chairs": ["Tank 1", "Healer 1"]},
    )

    rows = service.list_archive()
    assert len(rows) == 1
    assert rows[0].id == archive_id
    assert rows[0].payload == {"chairs": ["Tank 1", "Healer 1"]}


def test_archive_rejects_missing_identity_before_mutation(tmp_path: Path) -> None:
    service, _member_id = _service(tmp_path)

    with pytest.raises(ValueError):
        service.archive(entity_type="", display_name="")

    assert service.list_archive() == ()
