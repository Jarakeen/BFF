from pathlib import Path
from types import SimpleNamespace

from ui.application_window_composition import compose_application_window
from ui.roster_sub_terminology_support import apply_roster_sub_terminology


class _Combo:
    def __init__(self, values):
        self.values = list(values)

    def count(self):
        return len(self.values)

    def itemText(self, index):
        return self.values[index]

    def setItemText(self, index, value):
        self.values[index] = value


def test_roster_sub_terminology_applies_to_constructed_page_instance() -> None:
    combo = _Combo(["All", "Active", "Bench", "Inactive"])
    page = SimpleNamespace(show_combo=combo)

    apply_roster_sub_terminology(page)

    assert combo.values == ["All", "Active", "Sub", "Inactive"]


def test_application_window_composition_applies_roster_instance_features() -> None:
    combo = _Combo(["All", "Bench"])
    window = SimpleNamespace(
        pages={"roster_page": SimpleNamespace(show_combo=combo)}
    )

    compose_application_window(window)

    assert combo.values == ["All", "Sub"]


def test_roster_sub_terminology_no_longer_replaces_roster_class_methods() -> None:
    support = Path("ui/roster_sub_terminology_support.py").read_text(encoding="utf-8")
    bootstrap = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert "RosterPage._build_ui =" not in support
    assert "original_build_ui" not in support
    assert "install_roster_sub_terminology_support" not in bootstrap


def test_application_composes_instance_helpers_after_main_window_construction() -> None:
    source = Path("app.py").read_text(encoding="utf-8")

    assert "from ui.application_window_composition import compose_application_window" in source
    constructed = source.index("window = MainWindow()")
    composed = source.index("compose_application_window(window)")
    first_navigation = source.index('window.show_page("operations_console")')
    assert constructed < composed < first_navigation
