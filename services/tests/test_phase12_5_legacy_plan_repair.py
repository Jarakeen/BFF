from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import (
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
from services.phase12_5_legacy_plan_repair import Phase125LegacyPlanRepairService
from services.roster_service import RosterService


def _services(tmp_path: Path):
    db = EsoDatabase(tmp_path / "eso.db")
    plans = GeneratedRosterPlanService(db)
    roster = RosterService(db)
    repair = Phase125LegacyPlanRepairService(plans=plans, roster=roster)
    return db, plans, roster, repair


def _delete_team_identity(db: EsoDatabase, name: str) -> None:
    row = db.execute("SELECT id FROM team WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
    if row is not None:
        db.execute("DELETE FROM team_member WHERE team_id = ?", (row["id"],))
        db.execute("DELETE FROM team WHERE id = ?", (row["id"],))
        db.commit()


def _legacy_plan(plans: GeneratedRosterPlanService, *, source_kind: str = "saved_build"):
    return plans.save_plan(
        name="Godslayer Composition",
        goal="Godslayer",
        difficulty="Veteran Hardmode",
        slots=(
            GeneratedRosterPlanSlot(
                slot_name="Healer 1",
                kind="prescribed_recruit",
                player_name="Magrat",
                character_name="Magrat",
                eso_class="Warden",
                build_name="DF Healer",
                role="Healer",
                source_kind=source_kind,
                source_name="Magrat",
                unresolved="Legacy row.",
            ),
            GeneratedRosterPlanSlot(
                slot_name="Healer 2",
                kind="open_recruit",
                player_name="Recruitment Needed",
                character_name="",
                eso_class="Any class",
                build_name="Composition requirement",
                role="Healer",
            ),
        ),
    )


def _builds() -> BuildRoster:
    return BuildRoster(
        Members=[
            PlayerBuild(
                Name="Magrat",
                Gamertag="@keen",
                BuildName="DF Healer",
                EsoClass="Warden",
                Role="Healer",
                Mundus="The Ritual",
            )
        ]
    )


def test_inspect_reports_missing_identity_and_only_uniquely_provable_saved_chair(tmp_path: Path) -> None:
    db, plans, roster, repair = _services(tmp_path)
    plan = _legacy_plan(plans)
    _delete_team_identity(db, plan.name)
    roster.create_member(
        RosterMember(
            PlayerName="@keen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            Team="Other Team",
        )
    )

    result = repair.inspect(
        plan=plan,
        builds=_builds(),
        roster_members=tuple(roster.list_members()),
    )

    assert result.team_identity_missing is True
    assert result.promotable_slots == ("Healer 1",)
    assert result.ambiguous_slots == ()
    assert result.blocked_source_slots == ()
    assert result.normalizable_slots == ()


def test_apply_backfills_identity_promotes_saved_chair_and_preserves_other_memberships(tmp_path: Path) -> None:
    db, plans, roster, repair = _services(tmp_path)
    plan = _legacy_plan(plans)
    _delete_team_identity(db, plan.name)
    member_id = roster.create_member(
        RosterMember(
            PlayerName="@keen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            Team="Other Team",
        )
    )

    repaired = repair.apply(
        plan=plan,
        builds=_builds(),
        roster_members=tuple(roster.list_members()),
    )

    assert "Godslayer Composition" in roster.list_team_names()
    healer = next(slot for slot in repaired.slots if slot.slot_name == "Healer 1")
    assert healer.kind == "saved"
    assert healer.build_name == "DF Healer"
    assert healer.eso_class == "Warden"

    member = roster.get_member(member_id)
    assert member is not None
    assert set(value.strip() for value in member.Team.split(",")) == {
        "Other Team",
        "Godslayer Composition",
    }


def test_esologs_player_identity_is_never_promoted_and_is_normalizable(tmp_path: Path) -> None:
    _db, plans, roster, repair = _services(tmp_path)
    plan = _legacy_plan(plans, source_kind="esologs_snapshot")
    roster.create_member(
        RosterMember(
            PlayerName="@keen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
        )
    )

    result = repair.inspect(
        plan=plan,
        builds=_builds(),
        roster_members=tuple(roster.list_members()),
    )

    assert result.promotable_slots == ()
    assert result.blocked_source_slots == ("Healer 1",)
    assert result.normalizable_slots == ("Healer 1",)


def test_ambiguous_missing_exact_build_is_normalized_and_original_identity_is_preserved(tmp_path: Path) -> None:
    _db, plans, roster, repair = _services(tmp_path)
    plan = _legacy_plan(plans)
    roster.create_member(
        RosterMember(
            PlayerName="@keen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
        )
    )
    builds = BuildRoster(
        Members=[PlayerBuild(Name="Magrat", BuildName="Different Build", EsoClass="Warden")]
    )

    before = repair.inspect(
        plan=plan,
        builds=builds,
        roster_members=tuple(roster.list_members()),
    )
    assert before.promotable_slots == ()
    assert before.ambiguous_slots == ("Healer 1",)
    assert before.normalizable_slots == ("Healer 1",)

    repaired = repair.apply(
        plan=plan,
        builds=builds,
        roster_members=tuple(roster.list_members()),
    )
    healer = next(slot for slot in repaired.slots if slot.slot_name == "Healer 1")
    assert healer.kind == "prescribed_recruit"
    assert healer.player_name == "Recruitment Needed"
    assert healer.character_name == ""
    assert healer.build_name == "DF Healer"
    assert healer.source_name == "Magrat"

    evidence = repair.legacy_assignment_evidence(plan.name, "Healer 1")
    assert evidence is not None
    assert evidence["player_name"] == "Magrat"
    assert evidence["character_name"] == "Magrat"
    assert evidence["build_name"] == "DF Healer"
    assert evidence["source_kind"] == "saved_build"

    after = repair.inspect(
        plan=repaired,
        builds=builds,
        roster_members=tuple(roster.list_members()),
    )
    assert after.ambiguous_slots == ()
    assert after.normalizable_slots == ()


def test_blocked_source_normalization_preserves_source_evidence(tmp_path: Path) -> None:
    _db, plans, roster, repair = _services(tmp_path)
    plan = _legacy_plan(plans, source_kind="reference_template")

    repaired = repair.apply(
        plan=plan,
        builds=_builds(),
        roster_members=tuple(roster.list_members()),
    )

    healer = next(slot for slot in repaired.slots if slot.slot_name == "Healer 1")
    assert healer.kind == "prescribed_recruit"
    assert healer.player_name == "Recruitment Needed"
    assert healer.source_kind == "reference_template"
    assert healer.source_name == "Magrat"

    evidence = repair.legacy_assignment_evidence(plan.name, "Healer 1")
    assert evidence is not None
    assert evidence["player_name"] == "Magrat"
    assert evidence["source_kind"] == "reference_template"
