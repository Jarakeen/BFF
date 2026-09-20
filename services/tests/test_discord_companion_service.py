from pathlib import Path

from models.raid_plan import RaidPlan, RaidPlanMember
from models.roster_model import RosterMember
from services.discord_companion_service import FoundryDockDiscordCompanionService
from services.eso_database import EsoDatabase
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService


def _service(tmp_path: Path) -> FoundryDockDiscordCompanionService:
    db = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(db)
    member_id = roster.create_member(
        RosterMember(
            PlayerName="Rylo",
            CharacterName="Rylosorc",
            EsoClass="Sorcerer",
            PrimaryRole="DD",
            DiscordName="rylo-discord",
        )
    )
    repository = RaidPlanRepository(tmp_path / "raid_plans.json")
    repository.save(
        RaidPlan(
            plan_id="plan-1",
            trial_id="sunspire",
            name="GS Warmup",
            team_name="Performance Mode",
            status="active",
            members=(
                RaidPlanMember(
                    seat_id="dd-1",
                    gamertag="Rylo",
                    roster_member_id=member_id,
                    character_name="Rylosorc",
                    role="DD",
                    eso_class="Sorcerer",
                    selected_build_name="Corpsebuster + Null Arca",
                    planned_gear_sets=("Corpsebuster", "Null Arca"),
                    primary_assignment="Major Vulnerability",
                ),
            ),
        )
    )
    return FoundryDockDiscordCompanionService(
        plan_repository=repository,
        roster_service=roster,
        data_dir=tmp_path,
    )


def test_build_brief_matches_personnel_discord_name(tmp_path: Path) -> None:
    service = _service(tmp_path)
    brief = service.build_brief(player_ref="rylo-discord")
    assert brief.player == "Rylo"
    assert brief.build == "Corpsebuster + Null Arca"
    assert "Major Vulnerability" in brief.assignments


def test_raid_brief_uses_active_plan_without_duplicate_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    brief = service.raid_brief()
    assert brief.plan_id == "plan-1"
    assert brief.members[0].gear_sets == ("Corpsebuster", "Null Arca")
