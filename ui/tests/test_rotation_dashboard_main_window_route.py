from __future__ import annotations

from pathlib import Path


def test_main_window_does_not_import_or_construct_rotation_builder() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")

    assert (
        "from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage"
        not in source
    )
    assert '"rotations": CanonicalRotationDashboardPage(),' not in source
    assert '"rotations": RotationDashboardPage(),' not in source
