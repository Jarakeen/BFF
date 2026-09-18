from pathlib import Path

from ui import city_raid_roster_workspace_page
from widgets import roster_actions


def test_city_players_actions_live_inside_player_record_card() -> None:
    source = Path(city_raid_roster_workspace_page.__file__).read_text(encoding="utf-8")

    assert "self.actions.configure_player_editor()" in source
    assert 'record_card.addWidget(self.actions)' in source
    assert "player_layout.addWidget(self.actions)" not in source


def test_player_editor_action_mode_is_new_save_cancel_without_refresh() -> None:
    source = Path(roster_actions.__file__).read_text(encoding="utf-8")

    assert 'self.new_button.setText("New")' in source
    assert 'self.save_button.setText("Save")' in source
    assert 'self.delete_button.setText("Cancel")' in source
    assert "self.delete_button.clicked.connect(self.cancelRequested.emit)" in source
    assert "self.refresh_button.hide()" in source


def test_city_players_cancel_discards_unsaved_edits() -> None:
    source = Path(city_raid_roster_workspace_page.__file__).read_text(encoding="utf-8")

    assert "self.actions.cancelRequested.connect(self._cancel_player_edit)" in source
    assert "member = self.roster_service.get_member(int(selected_id))" in source
    assert "self.record.load(member)" in source
    assert 'self.record.clear()' in source
