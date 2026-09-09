from pathlib import Path


def test_repo_root_shape_for_direct_script() -> None:
    script = Path(__file__).resolve().parents[1] / "audit_phase13_lokkestiiz_healer_profile.py"
    assert script.parent.name == "tools"
