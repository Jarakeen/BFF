from pathlib import Path

from ui import rotation_builder_v2_finish_support
from ui import rotation_dashboard_layout_support


def test_rotation_builder_v2_finish_is_installed_after_layout() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert "install_rotation_builder_v2_finish" in source
    assert "install_rotation_builder_v2_layout(page)" in source
    assert "install_rotation_builder_v2_finish(page)" in source


def test_finished_workspace_keeps_known_incomplete_planners_explicit() -> None:
    source = Path(rotation_builder_v2_finish_support.__file__).read_text(encoding="utf-8")

    assert 'enabled = mode == "Semi-static"' in source
    assert 'card.set_badge("PLANNING")' in source
    assert "planner obligation bridge is still under construction" in source


def test_top_context_card_owns_real_character_build_team_content_boss_and_difficulty_controls() -> None:
    source = Path(rotation_builder_v2_finish_support.__file__).read_text(encoding="utf-8")

    for token in (
        '"CHARACTER", page.character_combo',
        '"BUILD", page.build_combo',
        '"TEAM", page.rotation_team_combo',
        '"CONTENT / LOCATION", page.rotation_content_combo',
        '"BOSS", page.rotation_boss_combo',
        '"DIFFICULTY", page.rotation_threshold_difficulty_combo',
    ):
        assert token in source
    assert "card.body_layout.insertLayout(0, grid)" in source


def test_rotation_effective_scope_resolves_sparse_team_and_boss_variants() -> None:
    source = Path(rotation_builder_v2_finish_support.__file__).read_text(encoding="utf-8")

    assert "resolve_build_context(" in source
    assert "team_name=_team_name(bound_page)" in source
    assert "boss_name=_boss_name(bound_page)" in source
    assert "_rotation_effective_scope_active" in source
    assert "page.rotation_boss_combo.currentIndexChanged.connect(refresh_effective)" in source


def test_light_attack_profile_reaches_real_generation_request() -> None:
    source = Path(rotation_builder_v2_finish_support.__file__).read_text(encoding="utf-8")

    assert "replace(request, weave_light_attacks=weave)" in source
    assert "generation.generate_with_evidence = MethodType" in source
    assert "Do not rely on it" in source


def test_normal_builder_uses_canonical_recovery_heavy_fixed_point() -> None:
    source = Path(rotation_builder_v2_finish_support.__file__).read_text(encoding="utf-8")

    assert "RotationHeavySustainProjectionService" in source
    assert "generation.recovery_stabilization.stabilize(" in source
    assert "restoration_resolver_factory=restoration_factory" in source
    assert "completion_evidence_from_verified_reservations" in source
    assert "recovery_pressure_resolver=pressure_resolver" in source
    assert "_rotation_v2_last_recovery_projection" in source


def test_explicit_primary_resource_controls_sustain_projection() -> None:
    source = Path(rotation_builder_v2_finish_support.__file__).read_text(encoding="utf-8")

    assert 'selected == "Magicka"' in source
    assert 'kwargs["resource"] = ResourceType.MAGICKA' in source
    assert 'selected == "Stamina"' in source
    assert 'kwargs["resource"] = ResourceType.STAMINA' in source


def test_rules_surface_matches_mockup_sections_without_inventing_semantics() -> None:
    source = Path(rotation_builder_v2_finish_support.__file__).read_text(encoding="utf-8")

    for title in (
        "Detected from Build",
        "Team Assignments",
        "Encounter Windows",
        "Custom Rules",
    ):
        assert title in source
    assert "Nothing is inferred from role alone." in source
