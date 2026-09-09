import sqlite3

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.team_provider_canonical_workload_service import (
    TeamProviderCanonicalActionReference,
    TeamProviderCanonicalContribution,
    TeamProviderCanonicalWorkloadService,
)
from services.team_provider_coverage_service import (
    TeamProviderCoverageProfile,
    TeamProviderCoverageService,
)
from services.team_provider_temporal_coverage_service import (
    TeamProviderTemporalCoverageService,
    TeamProviderTemporalRequirement,
    TeamProviderTimedApplication,
)


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER NOT NULL,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                rank INTEGER,
                morph INTEGER,
                raw_name TEXT,
                cooldown REAL,
                cast_time REAL,
                channel_time REAL
            );
            CREATE TABLE skill_coefficient (
                skill_rank_id INTEGER NOT NULL,
                coefficient_number INTEGER NOT NULL,
                type TEXT,
                a REAL,
                b REAL,
                c REAL,
                r REAL,
                avg REAL
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                base_cost REAL,
                base_mechanic INTEGER,
                skill_line TEXT,
                description TEXT
            );

            INSERT INTO skill VALUES (1, 100, 'Provider Skill');
            INSERT INTO skill_rank VALUES (
                10, 1, 101, 4, 1, 'Provider Skill', 0, 1500, 0
            );
            INSERT INTO skill_coefficient VALUES (10, 1, '8', .1, 1, 0, 1, NULL);
            INSERT INTO ability VALUES (
                101, 'Provider Skill', 2700, 1, 'Restoration Staff', NULL
            );

            INSERT INTO skill VALUES (2, 200, 'Provider Ultimate');
            INSERT INTO skill_rank VALUES (
                20, 2, 202, 4, 1, 'Provider Ultimate', 0, 0, 0
            );
            INSERT INTO skill_coefficient VALUES (20, 1, '8', .1, 1, 0, 1, NULL);
            INSERT INTO ability VALUES (
                202, 'Provider Ultimate', 250, 8, 'Assault', NULL
            );

            INSERT INTO skill VALUES (3, 300, 'Hybrid Provider Skill');
            INSERT INTO skill_rank VALUES (
                30, 3, 303, 4, 1, 'Hybrid Provider Skill', 0, 0, 0
            );
            INSERT INTO skill_coefficient VALUES (30, 1, '8', .1, 1, 0, 1, NULL);
            INSERT INTO ability VALUES (
                303, 'Hybrid Provider Skill', 2700, 5, 'Restoration Staff', NULL
            );

            INSERT INTO skill VALUES (4, 400, 'Eternal Guardian');
            INSERT INTO skill_rank VALUES (
                40, 4, 404, 4, 1, 'Eternal Guardian', 0, 0, 0
            );
            INSERT INTO skill_coefficient VALUES (40, 1, '8', .1, 1, 0, 1, NULL);
            INSERT INTO ability VALUES (
                404, 'Eternal Guardian', 0, 8, 'Animal Companions',
                'Once summoned you can activate Guardian''s Wrath for 75 Ultimate.'
            );
            """
        )
    return path


def _build():
    build = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        Race="Breton",
        FrontBarSkills=[
            "Provider Skill",
            "Hybrid Provider Skill",
            "",
            "",
            "",
            "Provider Ultimate",
        ],
        BackBarSkills=["Unrelated Unknown Skill", "", "", "", "", ""],
    )
    build.Armor["Head"]["Weight"] = "Light"
    build.Armor["Shoulders"]["Weight"] = "Light"
    return build


def _progression():
    return CharacterProgression(owned_skill_lines=("Light Armor",))


def _plan(*actions):
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def test_projects_skill_cost_timing_and_slot_from_canonical_build(tmp_path):
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
        RotationAction(20.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
    )

    projection = TeamProviderCanonicalWorkloadService(_database(tmp_path)).project(
        alternative_id="skill provider",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderCanonicalContribution(
                build=_build(),
                progression=_progression(),
                plan=plan,
                provider_actions=(
                    TeamProviderCanonicalActionReference(0.0, 0, 0.5),
                    TeamProviderCanonicalActionReference(20.0, 0, 0.5),
                ),
            ),
        ),
        gcd_seconds_per_application=1.0,
    )

    workload = projection.workload
    assert workload.viable
    assert workload.provider_applications == 2
    assert workload.provider_refreshes == 1
    assert workload.provider_gcd_seconds == 2.0
    assert workload.provider_cast_channel_seconds == 3.0
    # Breton Magicka Mastery (7%) + two-piece Light Armor Evocation (3%).
    assert workload.resource_costs == (("magicka", 4860.0),)
    assert workload.ultimate_spent == 0.0
    assert workload.occupied_bar_slots == ("magrat:front:provider_skill",)
    assert workload.primary_role_displacement_seconds == 1.0
    assert not any(
        "Unrelated Unknown Skill" in item for item in workload.unresolved
    )


def test_projects_ordinary_ultimate_cost_without_calling_it_magicka(tmp_path):
    plan = _plan(
        RotationAction(
            10.0,
            0,
            RotationActionKind.ULTIMATE,
            "Provider Ultimate",
            "front",
        ),
    )

    projection = TeamProviderCanonicalWorkloadService(_database(tmp_path)).project(
        alternative_id="ultimate provider",
        effect_key="major force",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderCanonicalContribution(
                build=_build(),
                progression=_progression(),
                plan=plan,
                provider_actions=(
                    TeamProviderCanonicalActionReference(10.0, 0, 0.0),
                ),
            ),
        ),
        gcd_seconds_per_application=1.0,
    )

    assert projection.workload.viable
    assert projection.workload.resource_costs == ()
    assert projection.workload.ultimate_spent == 250.0
    assert projection.workload.provider_cast_channel_seconds == 0.0


def test_projects_each_side_of_compound_cost_after_build_modifiers(tmp_path):
    plan = _plan(
        RotationAction(
            0.0,
            0,
            RotationActionKind.SKILL,
            "Hybrid Provider Skill",
            "front",
        ),
    )

    projection = TeamProviderCanonicalWorkloadService(_database(tmp_path)).project(
        alternative_id="hybrid resource provider",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderCanonicalContribution(
                build=_build(),
                progression=_progression(),
                plan=plan,
                provider_actions=(TeamProviderCanonicalActionReference(0.0, 0, 0.0),),
            ),
        ),
        gcd_seconds_per_application=1.0,
    )

    assert projection.workload.viable
    assert projection.workload.resource_costs == (
        ("magicka", 2430.0),
        ("stamina", 2700.0),
    )


def test_unverified_armor_cost_modifier_blocks_partial_cost(tmp_path):
    build = _build()
    build.Armor["Chest"]["Weight"] = "Light"
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
    )

    projection = TeamProviderCanonicalWorkloadService(_database(tmp_path)).project(
        alternative_id="unverified three-piece light cost",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderCanonicalContribution(
                build=build,
                progression=_progression(),
                plan=plan,
                provider_actions=(TeamProviderCanonicalActionReference(0.0, 0, 0.0),),
            ),
        ),
        gcd_seconds_per_application=1.0,
    )

    assert not projection.workload.viable
    assert any(
        "not live-verified for 3 equipped Light pieces" in item
        for item in projection.workload.unresolved
    )


def test_missing_gcd_policy_stays_unresolved(tmp_path):
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
    )

    projection = TeamProviderCanonicalWorkloadService(_database(tmp_path)).project(
        alternative_id="missing GCD policy",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderCanonicalContribution(
                build=_build(),
                progression=_progression(),
                plan=plan,
                provider_actions=(TeamProviderCanonicalActionReference(0.0, 0, 0.0),),
            ),
        ),
        gcd_seconds_per_application=None,
    )

    assert not projection.workload.viable
    assert any(
        "unresolved GCD occupancy" in item
        for item in projection.workload.unresolved
    )


def test_saved_build_slot_mismatch_blocks_workload(tmp_path):
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider Skill", "back"),
    )

    projection = TeamProviderCanonicalWorkloadService(_database(tmp_path)).project(
        alternative_id="wrong bar",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderCanonicalContribution(
                build=_build(),
                progression=_progression(),
                plan=plan,
                provider_actions=(TeamProviderCanonicalActionReference(0.0, 0, 0.0),),
            ),
        ),
        gcd_seconds_per_application=1.0,
    )

    assert not projection.workload.viable
    assert any(
        "saved-build ownership is front" in item
        for item in projection.workload.unresolved
    )


def test_plan_and_saved_build_identity_must_match(tmp_path):
    build = _build()
    plan = RotationPlan(
        character_name="Someone Else",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(),
    )

    try:
        TeamProviderCanonicalWorkloadService(_database(tmp_path)).project(
            alternative_id="wrong owner",
            effect_key="minor courage",
            duration_seconds=60.0,
            recipient_coverage_met=True,
            temporal_coverage_met=True,
            contributions=(
                TeamProviderCanonicalContribution(
                    build=build,
                    progression=_progression(),
                    plan=plan,
                    provider_actions=(),
                ),
            ),
            gcd_seconds_per_application=1.0,
        )
    except ValueError as exc:
        assert "character does not match" in str(exc)
    else:
        raise AssertionError("expected mismatched saved-build identity to fail")


def test_coverage_results_override_stale_manual_success_flags(tmp_path):
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
    )
    recipient = TeamProviderCoverageService.evaluate(
        TeamProviderCoverageProfile("combat_prayer", 6, 1),
        required_recipients=12,
    )
    temporal = TeamProviderTemporalCoverageService.evaluate(
        TeamProviderTemporalRequirement("minor courage", 0.0, 60.0),
        applications=(TeamProviderTimedApplication("minor courage", "Magrat", 0.0, 60.0),),
    )

    projection = TeamProviderCanonicalWorkloadService(_database(tmp_path)).project(
        alternative_id="stale caller flags",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderCanonicalContribution(
                build=_build(),
                progression=_progression(),
                plan=plan,
                provider_actions=(TeamProviderCanonicalActionReference(0.0, 0, 0.0),),
            ),
        ),
        gcd_seconds_per_application=1.0,
        recipient_coverage_result=recipient,
        temporal_coverage_result=temporal,
    )

    assert not projection.workload.viable
    assert not projection.workload.recipient_coverage_met
    assert projection.workload.temporal_coverage_met
    assert projection.workload.recipient_coverage_result is recipient
    assert projection.workload.temporal_coverage_result is temporal


def test_projects_persistent_ultimate_secondary_activation_cost(tmp_path):
    build = _build()
    build.BackBarSkills[-1] = "Eternal Guardian"
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.ULTIMATE, "Eternal Guardian", "back"),
    )

    projection = TeamProviderCanonicalWorkloadService(_database(tmp_path)).project(
        alternative_id="guardian activation",
        effect_key="guardian wrath",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributions=(
            TeamProviderCanonicalContribution(
                build=build,
                progression=_progression(),
                plan=plan,
                provider_actions=(TeamProviderCanonicalActionReference(10.0, 0, 0.0),),
            ),
        ),
        gcd_seconds_per_application=1.0,
    )

    assert projection.workload.viable
    assert projection.workload.ultimate_spent == 75.0
    assert projection.workload.resource_costs == ()


def test_project_from_coverage_uses_canonical_result_objects(tmp_path):
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Provider Skill", "front"),
    )
    recipient = TeamProviderCoverageService.evaluate(
        TeamProviderCoverageProfile("combat_prayer", 12, 1),
        required_recipients=12,
    )
    temporal = TeamProviderTemporalCoverageService.evaluate(
        TeamProviderTemporalRequirement("minor courage", 0.0, 60.0),
        applications=(
            TeamProviderTimedApplication("minor courage", "Magrat", 0.0, 60.0),
        ),
    )

    projection = TeamProviderCanonicalWorkloadService(
        _database(tmp_path)
    ).project_from_coverage(
        alternative_id="canonical coverage",
        effect_key="minor courage",
        duration_seconds=60.0,
        recipient_coverage_result=recipient,
        temporal_coverage_result=temporal,
        contributions=(
            TeamProviderCanonicalContribution(
                build=_build(),
                progression=_progression(),
                plan=plan,
                provider_actions=(
                    TeamProviderCanonicalActionReference(0.0, 0, 0.0),
                ),
            ),
        ),
        gcd_seconds_per_application=1.0,
    )

    assert projection.workload.viable
    assert projection.workload.recipient_coverage_result is recipient
    assert projection.workload.temporal_coverage_result is temporal
