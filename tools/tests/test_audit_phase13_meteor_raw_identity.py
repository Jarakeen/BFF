from pathlib import Path

import tools.audit_phase13_meteor_raw_identity as tool


def test_resolve_logs_database_uses_keyword_roots(monkeypatch, tmp_path: Path) -> None:
    discovered = tmp_path / "logs.db"
    captured: dict[str, tuple[Path, ...]] = {}

    def fake_discover(*, roots: tuple[Path, ...]) -> tuple[Path, ...]:
        captured["roots"] = roots
        return (discovered,)

    monkeypatch.setattr(tool, "discover", fake_discover)
    monkeypatch.setattr(tool, "get_data_dir", lambda: tmp_path / "configured")

    assert tool._resolve_logs_database(None) == discovered
    assert captured["roots"] == (
        tmp_path / "configured",
        tool.ROOT / "data",
        tool.ROOT / "user_data",
        tool.ROOT / "research",
    )


def test_resolve_logs_database_preserves_explicit_path(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit.db"
    assert tool._resolve_logs_database(explicit) == explicit
