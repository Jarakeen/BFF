from pathlib import Path

from tools.migrate_broadcast_resources import migrate


def test_migrate_broadcast_resources_copies_weather_and_creates_blank(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    weather = data_dir / "Weather"
    weather.mkdir(parents=True)
    (weather / "Clear.png").write_bytes(b"weather")
    (data_dir / "check.png").write_bytes(b"check")

    destination = tmp_path / "modules" / "broadcast" / "resources"

    copied, skipped = migrate(data_dir=data_dir, destination=destination)

    assert copied == 3
    assert skipped == 0
    assert (destination / "Weather" / "Clear.png").read_bytes() == b"weather"
    assert (destination / "check.png").read_bytes() == b"check"
    assert (destination / "blank.png").is_file()
    assert (destination / "blank.png").stat().st_size > 0


def test_migrate_broadcast_resources_preserves_existing_destination(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "check.png").write_bytes(b"legacy")

    destination = tmp_path / "resources"
    destination.mkdir()
    (destination / "check.png").write_bytes(b"keep")
    (destination / "blank.png").write_bytes(b"blank")

    copied, skipped = migrate(data_dir=data_dir, destination=destination)

    assert copied == 0
    assert skipped == 1
    assert (destination / "check.png").read_bytes() == b"keep"
    assert (destination / "blank.png").read_bytes() == b"blank"
