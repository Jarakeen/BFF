from pathlib import Path
from types import SimpleNamespace

from ui.application_window_composition import compose_application_window
from ui.gear_lookup_description_cleanup_support import (
    apply_gear_lookup_description_cleanup,
)
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


class _Signal:
    def __init__(self) -> None:
        self.handlers = []

    def connect(self, handler) -> None:
        self.handlers.append(handler)

    def emit(self) -> None:
        for handler in tuple(self.handlers):
            handler(None, None)


class _Label:
    def __init__(self, text: str) -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setText(self, value: str) -> None:
        self.value = value


class _Results:
    def __init__(self) -> None:
        self.currentItemChanged = _Signal()


def _gear_page(text: str):
    return SimpleNamespace(results=_Results(), bonuses=_Label(text))


def test_roster_sub_terminology_applies_to_constructed_page_instance() -> None:
    combo = _Combo(["All", "Active", "Bench", "Inactive"])
    page = SimpleNamespace(show_combo=combo)

    apply_roster_sub_terminology(page)

    assert combo.values == ["All", "Active", "Sub", "Inactive"]


def test_gear_lookup_cleanup_applies_after_normal_selection_render() -> None:
    page = _gear_page("|cFFAA00(5 items) Weapon and Spell Damage|r")

    apply_gear_lookup_description_cleanup(page)

    assert page.bonuses.text() == "(5 items) Weapon and Spell Damage"
    assert len(page.results.currentItemChanged.handlers) == 1

    page.bonuses.setText("|c00FF00Fresh selection|r")
    page.results.currentItemChanged.emit()
    assert page.bonuses.text() == "Fresh selection"

    apply_gear_lookup_description_cleanup(page)
    assert len(page.results.currentItemChanged.handlers) == 1


def test_application_window_composition_applies_instance_features() -> None:
    combo = _Combo(["All", "Bench"])
    gear_page = _gear_page("|cFFFFFFGear bonus|r")
    window = SimpleNamespace(
        pages={
            "roster_page": SimpleNamespace(show_combo=combo),
            "gear_lookup": gear_page,
        }
    )

    compose_application_window(window)

    assert combo.values == ["All", "Sub"]
    assert gear_page.bonuses.text() == "Gear bonus"


def test_migrated_instance_helpers_no_longer_replace_page_class_methods() -> None:
    roster_support = Path("ui/roster_sub_terminology_support.py").read_text(
        encoding="utf-8"
    )
    gear_support = Path("ui/gear_lookup_description_cleanup_support.py").read_text(
        encoding="utf-8"
    )
    bootstrap = Path("ui/application_workspace_bootstrap.py").read_text(
        encoding="utf-8"
    )

    assert "RosterPage._build_ui =" not in roster_support
    assert "original_build_ui" not in roster_support
    assert "install_roster_sub_terminology_support" not in bootstrap
    assert "GearLookupPage._show_selected =" not in gear_support
    assert "_ORIGINAL_SHOW_SELECTED" not in gear_support


def test_application_composes_instance_helpers_after_main_window_construction() -> None:
    source = Path("app.py").read_text(encoding="utf-8")

    assert "from ui.application_window_composition import compose_application_window" in source
    constructed = source.index("window = MainWindow()")
    composed = source.index("compose_application_window(window)")
    first_navigation = source.index('window.show_page("operations_console")')
    assert constructed < composed < first_navigation
