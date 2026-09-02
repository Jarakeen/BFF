from pathlib import Path

import services.optional_modules as optional_modules


def _install_fake_broadcast(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "modules" / "broadcast" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(optional_modules, "_BROADCAST_MANIFEST", manifest)


def test_broadcast_enabled_by_default(monkeypatch, tmp_path):
    _install_fake_broadcast(monkeypatch, tmp_path)
    monkeypatch.delenv("BFF_BROADCAST_ENABLED", raising=False)
    assert optional_modules.broadcast_enabled() is True


def test_broadcast_can_be_disabled(monkeypatch, tmp_path):
    _install_fake_broadcast(monkeypatch, tmp_path)
    monkeypatch.setenv("BFF_BROADCAST_ENABLED", "0")
    assert optional_modules.broadcast_enabled() is False


def test_broadcast_accepts_explicit_enabled_value(monkeypatch, tmp_path):
    _install_fake_broadcast(monkeypatch, tmp_path)
    monkeypatch.setenv("BFF_BROADCAST_ENABLED", "true")
    assert optional_modules.broadcast_enabled() is True


def test_broadcast_is_disabled_when_module_is_not_installed(monkeypatch, tmp_path):
    manifest = tmp_path / "missing" / "manifest.json"
    monkeypatch.setattr(optional_modules, "_BROADCAST_MANIFEST", manifest)
    monkeypatch.setenv("BFF_BROADCAST_ENABLED", "true")

    assert optional_modules.broadcast_installed() is False
    assert optional_modules.broadcast_enabled() is False
