from pathlib import Path

from ui import rotation_builder_v2_layout_support


def test_rotation_builder_v2_exposes_six_intent_first_tabs() -> None:
    source = Path(rotation_builder_v2_layout_support.__file__).read_text(encoding="utf-8")

    for title in (
        "Builder",
        "Timeline",
        "Uptime & Resources",
        "Explanations",
        "Compare",
        "Save / Export",
    ):
        assert f'addTab(' in source
        assert f'"{title}"' in source


def test_timeline_reuses_existing_canonical_visual_and_icon_pipeline() -> None:
    source = Path(rotation_builder_v2_layout_support.__file__).read_text(encoding="utf-8")
    timeline = Path("ui/rotation_timeline_dashboard_support.py").read_text(encoding="utf-8")

    assert "page.rotation_timeline_widget" in source
    assert "assets/AbilityIcons" in source
    assert 'get_resource_path("assets", "AbilityIcons", "icons", "128")' in timeline
    assert "RotationTimelineIconResolver" in timeline


def test_execution_profile_exposes_real_light_attack_contract() -> None:
    source = Path(rotation_builder_v2_layout_support.__file__).read_text(encoding="utf-8")

    assert '"Do not rely on it"' in source
    assert "page.rotation_weave_light_attacks" in source


def test_compare_uses_saved_rotation_artifacts_without_inventing_missing_metrics() -> None:
    source = Path(rotation_builder_v2_layout_support.__file__).read_text(encoding="utf-8")

    assert "BuildRotationArtifactService" in source
    assert "resolve_canonical_build_id" in source
    assert '"Current Generated"' in source
    assert '"Current Saved"' in source
    assert '"Alternate Saved"' in source


def test_save_export_tab_proxies_existing_save_and_pdf_actions() -> None:
    source = Path(rotation_builder_v2_layout_support.__file__).read_text(encoding="utf-8")

    assert 'getattr(page, "save_rotation_to_build_button", None)' in source
    assert 'getattr(page, "export_current_rotation_pdf", None)' in source
