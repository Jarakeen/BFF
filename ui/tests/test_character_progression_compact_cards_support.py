from pathlib import Path

from ui import character_progression_compact_cards_support
from ui import build_progression_scroll_fix


def test_progression_skill_families_use_multi_column_cards_not_toolbox() -> None:
    source = Path(character_progression_compact_cards_support.__file__).read_text(encoding="utf-8")

    assert "CARD_COLUMNS = 3" in source
    assert "FoundryCard(line)" in source
    assert "cards.addWidget(_line_card" in source
    assert "QToolBox" not in source


def test_compact_cards_keep_existing_progression_controls_and_storage_maps() -> None:
    source = Path(character_progression_compact_cards_support.__file__).read_text(encoding="utf-8")

    for text in (
        "Buy All",
        "Clear",
        "Unknown",
        "dialog._line_checks[line] = check",
        "dialog._passive_spins[name.casefold()] = (name, spin)",
        "_set_progression_spins",
    ):
        assert text in source


def test_compact_progression_cards_are_installed_before_embedded_panel_creation() -> None:
    source = Path(build_progression_scroll_fix.__file__).read_text(encoding="utf-8")

    assert "install_compact_progression_cards" in source
    assert "install_compact_progression_cards()" in source
    assert source.index("install_compact_progression_cards()") < source.index(
        "from ui.builds_page import BuildsPage"
    )
