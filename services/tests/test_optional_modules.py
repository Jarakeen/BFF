from services.optional_modules import broadcast_enabled


def test_broadcast_enabled_by_default(monkeypatch):
    monkeypatch.delenv("BFF_BROADCAST_ENABLED", raising=False)
    assert broadcast_enabled() is True


def test_broadcast_can_be_disabled(monkeypatch):
    monkeypatch.setenv("BFF_BROADCAST_ENABLED", "0")
    assert broadcast_enabled() is False


def test_broadcast_accepts_explicit_enabled_value(monkeypatch):
    monkeypatch.setenv("BFF_BROADCAST_ENABLED", "true")
    assert broadcast_enabled() is True
