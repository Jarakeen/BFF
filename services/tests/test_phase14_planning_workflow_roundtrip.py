from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from models.comp_plan_state import CompChairState
from models.roster_model import RosterMember
from services.build_catalog_service import BuildCatalogService
from services.build_service import BuildService
from services.canonical_build_bridge import CanonicalBuildBridge
from services.comp_build_persistence_service import CompBuildPersistenceService
from services.comp_plan_state_service import CompPlanStateService
from services.eso_database import EsoDatabase
from services.raid_plan_coverage_assignment_service import (
    RaidPlanCoverageAssignmentService,
)
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService
from services.raid_plan_repository import RaidPlanRepository
from services.raid_readiness_evidence_service import RaidReadinessEvidenceService
from services.roster_service import RosterService


def test_phase14_comp_to_raid_plan_build_coverage_readiness_round_trip(
    tmp_path: Path,
) -> None:
    """Planned Comp state stays Raid Plan-owned and never manufactures a Build."""
    database_path = tmp_path / "foundrydock.db"
    roster = RosterService(EsoDatabase(database_path))
    roster_member_id = roster.create_member(
        RosterMember(
            PlayerName="Jarakeen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            Status="Active",
        )
    )

    state = CompPlanStateService.new_unbound(
        raid_plan_name="Performance Mode GS",
        trial_id="sunspire",
        difficulty="Veteran Hardmode",
        chairs=(
            CompChairState(
                seat_id="Healer1",
                player_name="Jarakeen",
                roster_member_id=roster_member_id,
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                planned_gear_sets=("Perfected Grand Rejuvenation", "Spell Power Cure"),
                planned_skills=("Combat Prayer",),
                planned_mundus="The Ritual",
                primary_assignment="Major Courage",
                assignment_source="Spell Power Cure",
            ),
            CompChairState(
                seat_id="DD1",
                player_name="Recruit",
                role="DD",
                eso_class="Arcanist",
                planned_gear_sets=("Coral Riptide",),
            ),
        ),
    )

    build_persistence = CompBuildPersistenceService(tmp_path, database_path=database_path)
    assert BuildCatalogService(database_path).load_strict()["builds"] == []

    first = build_persistence.persist(state)
    first_healer = first.state.chair("Healer1")
    assert first_healer is not None
    assert first_healer.player_id
    assert first_healer.character_id
    assert first_healer.selected_build_id is None
    assert first_healer.build_source_kind == "planned"
    assert "Healer1" in first.saved_seats
    assert "DD1" in first.skipped_seats
    assert BuildCatalogService(database_path).load_strict()["builds"] == []
    assert not (tmp_path / "characters.json").exists()

    plan_id = CompPlanStateService.unique_raid_plan_id(first.state)
    plan = CompPlanStateService.to_new_raid_plan(first.state, plan_id=plan_id)
    repository = RaidPlanRepository(database_path)
    repository.save(plan)

    persisted = repository.get(plan_id)
    assert persisted is not None
    persisted_healer = persisted.member("Healer1")
    assert persisted_healer is not None
    assert persisted_healer.selected_build_id is None
    assert persisted_healer.planned_gear_sets == first_healer.planned_gear_sets

    rebound = CompPlanStateService.from_raid_plan(persisted)
    second = build_persistence.persist(rebound)
    second_healer = second.state.chair("Healer1")
    assert second_healer is not None
    assert second_healer.selected_build_id is None
    assert BuildCatalogService(database_path).load_strict()["builds"] == []

    final_plan = CompPlanStateService.to_raid_plan(second.state, base_plan=persisted)
    repository.save(final_plan)
    reloaded_plan = repository.get(plan_id)
    assert reloaded_plan == final_plan

    saved_builds = tuple(
        CanonicalBuildBridge(tmp_path / "builds.json", catalog_path=database_path).load().Members
    )
    assert saved_builds == ()

    scope = RaidPlanCoverageScopeService().compose(
        raid_plan=reloaded_plan,
        saved_builds=saved_builds,
        coverage_effect_names=("Major Courage",),
        total_chairs=len(reloaded_plan.members),
    )
    assert len(scope.members) == 1
    assert scope.members[0].seat_id == "Healer1"
    assert scope.members[0].build is None
    assert scope.primary_for("Major Courage") == ("Magrat",)
    assert any("DD1" in message for message in scope.unresolved)

    coverage = RaidPlanCoverageAssignmentService().review(
        effect_name="Major Courage",
        scope=scope,
        snapshot=SimpleNamespace(
            providers={"Major Courage": []},
            conditional_providers={"Major Courage": []},
        ),
    )
    assert coverage.counts_as_planned_coverage is True
    assert coverage.state == "assigned_unproven"
    assert coverage.label == "Covered • Planned"

    catalog = BuildCatalogService(database_path).load_strict()
    assert all(
        str(player.get("gamertag") or "").casefold() != "recruit"
        for player in catalog["players"]
    )
    assert catalog["builds"] == []
