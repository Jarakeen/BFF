from __future__ import annotations

from pathlib import Path


def test_main_window_constructs_only_owned_phase14_rotation_builder() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")

    assert "from ui.phase14_rotation_page import RotationBuilderPage" in source
    assert '"rotations": RotationBuilderPage(),' in source
    assert (
        "from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage"
        not in source
    )
    assert '"rotations": CanonicalRotationDashboardPage(),' not in source
    assert '"rotations": RotationDashboardPage(),' not in source


def test_phase14_rotation_page_does_not_import_legacy_dashboard_layers() -> None:
    source = Path("ui/phase14_rotation_page.py").read_text(encoding="utf-8")

    forbidden = (
        "rotation_dashboard_page",
        "rotation_dashboard_canonical_page",
        "rotation_dashboard_layout_support",
        "phase14_rotation_command_center_support",
        "rotation_builder_v2_layout_support",
        "rotation_builder_v2_finish_support",
        "rotation_builder_v2_compact_context_support",
        "rotation_builder_v2_runtime_repairs_support",
    )
    for module_name in forbidden:
        assert module_name not in source
