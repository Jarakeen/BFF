from pathlib import Path

from ui import performance_dashboard_immunity_compat


def test_compat_state_is_created_during_dashboard_build_not_only_load() -> None:
    source = Path(performance_dashboard_immunity_compat.__file__).read_text(encoding="utf-8")

    assert "original_build_ui = PerformanceDashboard.build_ui" in source
    assert "def build_ui_with_compat_aliases" in source
    assert "_ensure_compat_aliases(self)" in source
    assert "PerformanceDashboard.build_ui = build_ui_with_compat_aliases" in source


def test_hidden_tracked_effect_adapter_still_exists_for_model_persistence() -> None:
    source = Path(performance_dashboard_immunity_compat.__file__).read_text(encoding="utf-8")

    assert 'if not hasattr(widget, "tracked_effects_list")' in source
    assert "legacy_list = QListWidget(widget)" in source
    assert "widget.tracked_effects_list = legacy_list" in source
