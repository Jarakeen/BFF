from __future__ import annotations

from pathlib import Path


def test_the_console_ops_engine_is_not_a_public_engine_package_export() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "engine" / "__init__.py").read_text(encoding="utf-8")

    assert "from .operations import TheConsoleOpsEngine" not in source
    assert '"TheConsoleOpsEngine"' not in source
