import json
import tempfile
from pathlib import Path

import pytest

from minmax.dd_damage import DDDamageEvent
from minmax.evaluation_context import EvaluationContext
from minmax.group_effects import GroupEffect
from minmax.role import Role
from minmax.saved_build_team_comparison import SavedBuildTeamComparisonAdapter
from models.build_model import BuildRoster, PlayerBuild


@pytest.fixture
def temp_builds_json():
    """Create temporary builds.json with test fixtures."""
    builds_data = {
        "Members": [
            {
                "Name": "Player One",
                "BuildName": "Build Alpha",
                "EsoClass": "Nightblade",
                "FrontBarSkills": ["Skill A", "Skill B", "Skill C", "Skill D", "Skill E"],
                "BackBarSkills": ["Skill X", "Skill Y", "Skill Z", "", ""],
            },
            {
                "Name": "Player Two",
                "BuildName": "Build Beta",
                "EsoClass": "Sorcerer",
                "FrontBarSkills": ["Skill 1", "Skill 2", "Skill 3", "Skill 4", "Skill 5"],
                "BackBarSkills": [],  # No back bar skills
            },
            {
                "Name": "Player Three",
                "BuildName": "Empty Back Bar",
                "EsoClass": "Dragonknight",
                "FrontBarSkills": ["Skill X", "Skill Y", "", "", ""],
                "BackBarSkills": [],  # Explicitly no back bar skills for test
            },
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(builds_data, f)
        path = Path(f.name)
    
    yield path
    
    # Cleanup
    path.unlink()


@pytest.fixture
def temp_database_path():
    """Return path to test database."""
    # Use the existing test database
    db_path = Path(__file__).resolve().parents[2] / "data" / "eso.db"
    if not db_path.exists():
        pytest.skip(f"Test database not found at {db_path}")
    return db_path


@pytest.fixture
def adapter(temp_builds_json, temp_database_path):
    """Create adapter with test fixtures."""
    return SavedBuildTeamComparisonAdapter(
        builds_path=temp_builds_json,
        database_path=temp_database_path,
    )


def test_two_named_saved_builds_resolve_deterministically(adapter):
    """Verify that named saves builds can be found and are consistent."""
    event = DDDamageEvent(base_value=1000.0)
    context = EvaluationContext()
    
    # First comparison
    comparison1, baseline1, candidate1 = adapter.compare(
        baseline_build_name="Build Alpha",
        baseline_active_bar="front",
        candidate_build_name="Build Beta",
        candidate_active_bar="front",
        event=event,
        context=context,
    )
    
    # Second comparison with same inputs
    comparison2, baseline2, candidate2 = adapter.compare(
        baseline_build_name="Build Alpha",
        baseline_active_bar="front",
        candidate_build_name="Build Beta",
        candidate_active_bar="front",
        event=event,
        context=context,
    )
    
    # Results should be identical
    assert baseline1.dd_expected_damage == baseline2.dd_expected_damage
    assert candidate1.dd_expected_damage == candidate2.dd_expected_damage
    assert comparison1.baseline_evaluation.group_damage == comparison2.baseline_evaluation.group_damage
    assert comparison1.candidate_evaluation.group_damage == comparison2.candidate_evaluation.group_damage


def test_player_personal_damage_traceable_to_dd_event(adapter):
    """Verify that personal damage is traceable to DD event evaluation."""
    event = DDDamageEvent(base_value=500.0)
    context = EvaluationContext()
    
    comparison, baseline, candidate = adapter.compare(
        baseline_build_name="Build Alpha",
        baseline_active_bar="front",
        candidate_build_name="Build Beta",
        candidate_active_bar="front",
        event=event,
        context=context,
    )
    
    # Evidence should record the exact event
    assert baseline.dd_event == event
    assert candidate.dd_event == event
    
    # Evidence should record the exact context
    assert baseline.evaluation_context == context
    assert candidate.evaluation_context == context
    
    # DD expected damage should be recorded
    assert baseline.dd_expected_damage > 0  # Base 500 is minimum
    assert candidate.dd_expected_damage > 0
    
    # RosterCandidate personal_damage should match DD evaluation
    assert baseline.roster_candidate.personal_damage == baseline.dd_expected_damage
    assert candidate.roster_candidate.personal_damage == candidate.dd_expected_damage
    
    # Group evaluation should use the personal damage
    assert baseline.roster_candidate.personal_damage in (
        comparison.baseline_evaluation.group_damage,
    )


def test_declared_group_effect_changes_modeled_result(adapter):
    """Verify that declared group effects are applied and attributed."""
    event = DDDamageEvent(base_value=1000.0)
    context = EvaluationContext()
    
    # Compare without group effect
    comparison_base, baseline_base, candidate_base = adapter.compare(
        baseline_build_name="Build Alpha",
        baseline_active_bar="front",
        candidate_build_name="Build Beta",
        candidate_active_bar="front",
        event=event,
        context=context,
    )
    
    # Compare with group effect on candidate
    group_effect = GroupEffect(
        source="Support Buffer",
        effect_type="damage_amplification",
        value=10.0,
        affected_roles=frozenset({Role.DD}),
        affects_source=False,
    )
    
    comparison_with_effect, baseline_with, candidate_with = adapter.compare(
        baseline_build_name="Build Alpha",
        baseline_active_bar="front",
        candidate_build_name="Build Beta",
        candidate_active_bar="front",
        event=event,
        context=context,
        group_effects=(group_effect,),
    )
    
    # Baseline should be unchanged
    assert comparison_base.baseline_evaluation.group_damage == comparison_with_effect.baseline_evaluation.group_damage
    
    # Candidate should be higher with the effect
    assert comparison_with_effect.candidate_evaluation.group_damage > comparison_base.candidate_evaluation.group_damage
    
    # The effect should be recorded in candidate's evaluation
    assert len(comparison_with_effect.candidate_evaluation.effect_contributions) > 0
    contrib = comparison_with_effect.candidate_evaluation.effect_contributions[0]
    assert contrib.source_name == "Support Buffer"
    assert contrib.effect_type == "damage_amplification"


def test_missing_build_fails_clearly(adapter):
    """Verify that missing builds produce clear errors."""
    event = DDDamageEvent(base_value=1000.0)
    context = EvaluationContext()
    
    with pytest.raises(ValueError, match="Saved build not found"):
        adapter.compare(
            baseline_build_name="Nonexistent Build",
            baseline_active_bar="front",
            candidate_build_name="Build Beta",
            candidate_active_bar="front",
            event=event,
            context=context,
        )


def test_missing_active_bar_fails_clearly(adapter):
    """Verify that missing active bar skills produce clear errors."""
    event = DDDamageEvent(base_value=1000.0)
    context = EvaluationContext()
    
    with pytest.raises(ValueError, match="no skills"):
        adapter.compare(
            baseline_build_name="Empty Back Bar",
            baseline_active_bar="back",  # This build has no back bar skills
            candidate_build_name="Build Beta",
            candidate_active_bar="front",
            event=event,
            context=context,
        )


def test_invalid_active_bar_name_fails(adapter):
    """Verify that invalid bar names are rejected."""
    event = DDDamageEvent(base_value=1000.0)
    context = EvaluationContext()
    
    with pytest.raises(ValueError, match="Invalid active_bar"):
        adapter.compare(
            baseline_build_name="Build Alpha",
            baseline_active_bar="invalid",
            candidate_build_name="Build Beta",
            candidate_active_bar="front",
            event=event,
            context=context,
        )


def test_no_source_data_modified(adapter, temp_builds_json):
    """Verify that the comparison does not modify source data files."""
    original_content = temp_builds_json.read_text()
    original_mtime = temp_builds_json.stat().st_mtime
    
    event = DDDamageEvent(base_value=1000.0)
    context = EvaluationContext()
    
    # Run comparison
    adapter.compare(
        baseline_build_name="Build Alpha",
        baseline_active_bar="front",
        candidate_build_name="Build Beta",
        candidate_active_bar="front",
        event=event,
        context=context,
    )
    
    # Verify file content unchanged
    new_content = temp_builds_json.read_text()
    assert original_content == new_content
    
    # Verify file was not modified
    new_mtime = temp_builds_json.stat().st_mtime
    assert original_mtime == new_mtime


def test_comparison_result_is_rankable_without_unresolved_effects(adapter):
    """Verify that comparison results are rankable when no unresolved effects exist."""
    event = DDDamageEvent(base_value=1000.0)
    context = EvaluationContext()
    
    comparison, baseline, candidate = adapter.compare(
        baseline_build_name="Build Alpha",
        baseline_active_bar="front",
        candidate_build_name="Build Beta",
        candidate_active_bar="front",
        event=event,
        context=context,
    )
    
    # Both evaluations should have no unresolved effects
    assert len(comparison.baseline_evaluation.unresolved_effects) == 0
    assert len(comparison.candidate_evaluation.unresolved_effects) == 0
    
    # Comparison should be rankable
    assert comparison.rankable
    
    # Should have a preferred team or none if tied
    preferred = comparison.preferred_team_name
    assert preferred in ("Build Alpha", "Build Beta", None)
