from pathlib import Path

from services.broadcast_state_migration import (
    BROADCAST_STATE_FILENAMES,
    migrate_legacy_broadcast_state,
)


def test_broadcast_state_migration_copies_legacy_files_without_deleting_source(tmp_path: Path) -> None:
    legacy = tmp_path / "data"
    target = tmp_path / "user_data" / "broadcast"
    legacy.mkdir()

    for filename in BROADCAST_STATE_FILENAMES:
        (legacy / filename).write_text(f"legacy:{filename}", encoding="utf-8")

    result = migrate_legacy_broadcast_state(legacy_dir=legacy, target_dir=target)

    assert result.copied == BROADCAST_STATE_FILENAMES
    assert result.preserved == ()
    assert result.missing == ()
    for filename in BROADCAST_STATE_FILENAMES:
        assert (legacy / filename).read_text(encoding="utf-8") == f"legacy:{filename}"
        assert (target / filename).read_text(encoding="utf-8") == f"legacy:{filename}"


def test_broadcast_state_migration_never_overwrites_existing_user_state(tmp_path: Path) -> None:
    legacy = tmp_path / "data"
    target = tmp_path / "user_data" / "broadcast"
    legacy.mkdir()
    target.mkdir(parents=True)

    filename = "CurrentBroadcast.json"
    (legacy / filename).write_text("legacy", encoding="utf-8")
    (target / filename).write_text("new-user-state", encoding="utf-8")

    result = migrate_legacy_broadcast_state(legacy_dir=legacy, target_dir=target)

    assert result.copied == ()
    assert result.preserved == (filename,)
    assert set(result.missing) == set(BROADCAST_STATE_FILENAMES) - {filename}
    assert (target / filename).read_text(encoding="utf-8") == "new-user-state"
