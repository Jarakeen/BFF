from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ui.roster_team_merge_visibility_support import _ensure_merge_button


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_merge_button_is_inserted_inside_nested_team_card_layout() -> None:
    _app()
    page = QWidget()
    outer = QVBoxLayout(page)
    card = QWidget()
    card_layout = QHBoxLayout(card)
    create = QPushButton("Create Team")
    delete = QPushButton("Delete Selected Team")
    card_layout.addWidget(create)
    card_layout.addWidget(delete)
    outer.addWidget(card)

    class FakeRosterPage:
        pass

    roster_page = FakeRosterPage()
    _ensure_merge_button(page, roster_page)

    labels = [
        card_layout.itemAt(index).widget().text()
        for index in range(card_layout.count())
        if isinstance(card_layout.itemAt(index).widget(), QPushButton)
    ]
    assert labels == ["Create Team", "Merge Teams…", "Delete Selected Team"]
    assert roster_page.merge_teams_button.text() == "Merge Teams…"


def test_visibility_support_installs_after_merge_workflow() -> None:
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")
    assert source.index("install_roster_team_merge_support()") < source.index(
        "install_roster_team_merge_visibility_support()"
    )
