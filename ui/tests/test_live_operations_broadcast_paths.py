from pathlib import Path


def test_live_operations_uses_shared_broadcast_path_contract():
    source = Path("ui/stream_elements_page.py").read_text(encoding="utf-8")

    assert "BroadcastPaths.from_settings(self.settings)" in source
    assert "events_path=self.broadcast_paths.stream_events" in source
    assert "session_path=self.broadcast_paths.stream_session" in source
    assert "boss_log_path=self.broadcast_paths.boss_log" in source
    assert "counters_folder=self.broadcast_paths.counters_folder" in source
    assert "archive_folder=self.broadcast_paths.archive_folder" in source
    assert "path = self.broadcast_paths.current_broadcast" in source

    assert 'Path(self.settings["StreamEventsPath"])' not in source
    assert 'Path(self.settings["StreamSessionPath"])' not in source
    assert 'Path(self.settings["BossLogPath"])' not in source
    assert 'Path(self.settings["CurrentBroadcastPath"])' not in source
