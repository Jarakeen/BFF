from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.evaluate_heavy_attack_restore import infer_base_restore


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "evaluate_heavy_attack_restore.py"


def test_infer_base_restore_with_cycle_of_life() -> None:
    inferred = infer_base_restore(
        observed_restore=3861,
        weapon_specific_percent=0.30,
    )

    assert abs(inferred - 2970.0) < 1e-9


def test_infer_base_restore_preserves_existing_modifier_order() -> None:
    inferred = infer_base_restore(
        observed_restore=4004,
        cp_percent=0.10,
        skill_percent=0.04,
        weapon_specific_percent=0.30,
    )

    expected = 4004 / (1.10 * 1.04 * 1.30)
    assert abs(inferred - expected) < 1e-9


def test_tool_prints_weapon_resource_and_inferred_base() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--weapon",
            "restoration_staff",
            "--observed-restore",
            "3861",
            "--weapon-specific-percent",
            "0.30",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Weapon:         restoration_staff" in result.stdout
    assert "Resource:       magicka" in result.stdout
    assert "Observed:       3861" in result.stdout
    assert "Inferred base:  2970.000000" in result.stdout
    assert "Nearest int:    2970" in result.stdout
