from __future__ import annotations

from pathlib import Path

from engine import config


def _freeze_paths(monkeypatch, *, app_root: Path, bundle_root: Path) -> None:
    monkeypatch.setattr(config.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config.sys, "executable", str(app_root / "FoundryDock.exe"))
    monkeypatch.setattr(config.sys, "_MEIPASS", str(bundle_root), raising=False)


def test_frozen_database_is_provisioned_from_bundled_seed(tmp_path, monkeypatch):
    app_root = tmp_path / "install"
    bundle_root = tmp_path / "bundle"
    seed = bundle_root / "_seed_data" / "eso.db"
    seed.parent.mkdir(parents=True)
    seed.write_bytes(b"canonical-seed")

    _freeze_paths(monkeypatch, app_root=app_root, bundle_root=bundle_root)

    target = config.ensure_default_database()

    assert target == app_root / "data" / "eso.db"
    assert target.read_bytes() == b"canonical-seed"


def test_frozen_database_provisioning_preserves_existing_database(tmp_path, monkeypatch):
    app_root = tmp_path / "install"
    bundle_root = tmp_path / "bundle"
    target = app_root / "data" / "eso.db"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"user-database")

    seed = bundle_root / "_seed_data" / "eso.db"
    seed.parent.mkdir(parents=True)
    seed.write_bytes(b"new-seed")

    _freeze_paths(monkeypatch, app_root=app_root, bundle_root=bundle_root)

    resolved = config.ensure_default_database()

    assert resolved == target
    assert target.read_bytes() == b"user-database"


def test_source_run_does_not_provision_missing_database(tmp_path, monkeypatch):
    monkeypatch.setattr(config.sys, "frozen", False, raising=False)
    monkeypatch.setattr(config, "get_data_dir", lambda: tmp_path / "data")

    target = config.ensure_default_database()

    assert target == tmp_path / "data" / "eso.db"
    assert not target.exists()
