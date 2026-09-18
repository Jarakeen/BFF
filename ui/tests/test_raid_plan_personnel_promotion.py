from pathlib import Path

from ui import raid_plan_persistence_page


def test_raid_plan_save_promotes_named_players_before_identity_resolution() -> None:
    source = Path(raid_plan_persistence_page.__file__).read_text(encoding="utf-8")

    assert "def _ensure_named_players_in_personnel" in source
    assert "self.roster_service.create_member(new_personnel_member(gamertag))" in source
    assert "self.refresh_personnel()" in source
    assert "created_players = self._ensure_named_players_in_personnel()" in source
    assert source.index("created_players = self._ensure_named_players_in_personnel()") < source.index(
        "plan = self.current_plan()"
    )
