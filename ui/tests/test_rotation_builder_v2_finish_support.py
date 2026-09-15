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


def test_light_attack_profile_reaches_real_generation_request() -> None:
    source = Path(rotation_builder_v2_finish_support.__file__).read_text(encoding="utf-8")

    assert "replace(request, weave_light_attacks=weave)" in source
    assert "generation.generate_with_evidence = MethodType" in source
    assert '"Do not rely on it"' in source


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
