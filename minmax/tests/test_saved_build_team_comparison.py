import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from minmax.dd_damage import DDDamageEvent
from minmax.evaluation_context import EvaluationContext
from minmax.group_effects import GroupEffect
from minmax.role import Role
from minmax.saved_build_team_comparison import (\n    SavedBuildRosterMember,\n    SavedBuildRosterScenario,\n    SavedBuildTeamComparisonAdapter,\n)
from minmax.stat_ids import StatId


class FakeProgressionAdapter:
    def resolve(self, build):
        return SimpleNamespace(
            resolved=True,
            character_id=f"id-{build.BuildName}",
            progression=SimpleNamespace(),
            unresolved=(),
        )


class FakeContextFactory:
    def build(self, *, build, **_kwargs):
        critical_chance = 0.2 if build.BuildName == "Build Alpha" else 0.5
        values = {
            StatId.WEAPON_DAMAGE: 2000.0,
            StatId.SPELL_DAMAGE: 2000.0,
            StatId.PHYSICAL_PENETRATION: 0.0,
            StatId.SPELL_PENETRATION: 0.0,
            StatId.CRITICAL_CHANCE: critical_chance,
            StatId.CRITICAL_DAMAGE: 0.5,
        }
        derived = {
            stat: SimpleNamespace(final_value=value)
            for stat, value in values.items()
        }
        return SimpleNamespace(
            core_state=SimpleNamespace(derived=derived),
            unresolved_gear_effects=(),
        )


@pytest.fixture
def builds_path(tmp_path: Path) -> Path:
    path = tmp_path / "builds.json"
    path.write_text(json.dumps({"Members": [
        {
            "Name": "Player One", "BuildName": "Build Alpha",
            "EsoClass": "Nightblade", "Role": "dd",
            "FrontBarSkills": ["Skill A"], "BackBarSkills": [],
        },
        {
            "Name": "Player Two", "BuildName": "Build Beta",
            "EsoClass": "Sorcerer", "Role": "dd",
            "FrontBarSkills": ["Skill B"], "BackBarSkills": [],
        },
    ]}), encoding="utf-8")
    return path


@pytest.fixture
def adapter(builds_path: Path, tmp_path: Path) -> SavedBuildTeamComparisonAdapter:
    return SavedBuildTeamComparisonAdapter(
        builds_path=builds_path,
        database_path=tmp_path / "eso.db",
        progression_adapter=FakeProgressionAdapter(),
        context_factory=FakeContextFactory(),
    )


def test_saved_build_static_context_changes_personal_damage(adapter):
    comparison, baseline, candidate = adapter.compare(
        "Build Alpha", "front", "Build Beta", "front",
        DDDamageEvent(base_value=1000.0), EvaluationContext(),
    )
    assert baseline.dd_expected_damage != candidate.dd_expected_damage
    assert baseline.roster_candidate.personal_damage == baseline.damage.final_damage
    assert candidate.roster_candidate.personal_damage == candidate.damage.final_damage
    assert comparison.preferred_team_name == "Build Beta"


def test_declared_candidate_effect_is_attributed(adapter):
    comparison, _baseline, _candidate = adapter.compare(
        "Build Alpha", "front", "Build Beta", "front",
        DDDamageEvent(base_value=1000.0), EvaluationContext(),
        group_effects=(GroupEffect(
            source="Player Two",
            effect_type="damage_amplification",
            value=10.0,
            affected_roles=frozenset({Role.DD}),
            affects_source=True,
        ),),
    )
    contribution = comparison.candidate_evaluation.effect_contributions[0]
    assert contribution.source_name == "Player Two"
    assert contribution.recipient_names == ("Player Two",)
    assert contribution.damage_added > 0.0


def test_missing_build_and_empty_bar_fail_clearly(adapter):
    with pytest.raises(ValueError, match="Saved build not found"):
        adapter.compare("missing", "front", "Build Beta", "front", DDDamageEvent(1))
    with pytest.raises(ValueError, match="has no skills"):
        adapter.compare("Build Alpha", "back", "Build Beta", "front", DDDamageEvent(1))



def test_shared_roster_attributes_provider_effect_to_other_member(adapter):
    scenario = SavedBuildRosterScenario(
        name="Two-player roster",
        members=(
            SavedBuildRosterMember(
                member_id="alpha",
                build_name="Build Alpha",
                active_bar="front",
                group_effects=(GroupEffect(
                    source="Alpha support effect",
                    effect_type="damage_amplification",
                    value=10.0,
                    affected_roles=frozenset({Role.DD}),
                    affects_source=False,
                ),),
            ),
            SavedBuildRosterMember(
                member_id="beta",
                build_name="Build Beta",
                active_bar="front",
            ),
        ),
    )

    result = adapter.evaluate_roster(
        scenario,
        DDDamageEvent(base_value=1000.0),
        EvaluationContext(),
    )

    contribution = result.group_evaluation.effect_contributions[0]
    assert contribution.source_name == "alpha"
    assert contribution.recipient_names == ("beta",)
    assert contribution.damage_added > 0.0
    assert tuple(
        row.roster_candidate.name for row in result.player_evidence
    ) == ("alpha", "beta")


def test_roster_scenario_rejects_duplicate_member_ids():
    with pytest.raises(ValueError, match="must be unique"):
        SavedBuildRosterScenario(
            name="Invalid",
            members=(
                SavedBuildRosterMember("same", "Build Alpha", "front"),
                SavedBuildRosterMember("SAME", "Build Beta", "front"),
            ),
        )


def test_compare_rosters_uses_shared_member_contributions(adapter):
    team_a = SavedBuildRosterScenario(
        name="Team A",
        members=(
            SavedBuildRosterMember("a-alpha", "Build Alpha", "front"),
            SavedBuildRosterMember("a-beta", "Build Beta", "front"),
        ),
    )
    team_b = SavedBuildRosterScenario(
        name="Team B",
        members=(
            SavedBuildRosterMember(
                "b-alpha",
                "Build Alpha",
                "front",
                group_effects=(GroupEffect(
                    source="Alpha support effect",
                    effect_type="damage_amplification",
                    value=10.0,
                    affected_roles=frozenset({Role.DD}),
                    affects_source=False,
                ),),
            ),
            SavedBuildRosterMember("b-beta", "Build Beta", "front"),
        ),
    )

    result = adapter.compare_rosters(
        team_a,
        team_b,
        DDDamageEvent(base_value=1000.0),
        EvaluationContext(),
    )

    assert result.comparison.rankable
    assert result.comparison.preferred_team_name == "Team B"
    assert result.comparison.modeled_damage_delta > 0.0
    assert (
        result.candidate.group_evaluation.effect_contributions[0].recipient_names
        == ("b-beta",)
    )
