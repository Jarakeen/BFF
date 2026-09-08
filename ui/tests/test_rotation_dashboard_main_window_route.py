from __future__ import annotations

from pathlib import Path


def test_main_window_routes_rotations_to_canonical_dashboard_page() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")

    assert (
        "from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage"
        in source
    )
    assert '"rotations": CanonicalRotationDashboardPage(),' in source
    assert '"rotations": RotationDashboardPage(),' not in source
