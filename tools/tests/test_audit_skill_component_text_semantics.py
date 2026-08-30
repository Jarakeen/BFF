import subprocess
import sys
from pathlib import Path

from tools.audit_skill_coefficient_slots import CoefficientSlotAuditRow
from tools.audit_skill_component_text_semantics import is_active_coefficient


ROOT = Path(__file__).resolve().parents[2]


def _row(*, coefficient_type: str, a: float, b: float, c: float, r: float):
    return CoefficientSlotAuditRow(
        skill_rank_id=1,
        coefficient_number=1,
        ability_id=2,
        name="Test",
        coefficient_type=coefficient_type,
        a=a,
        b=b,
        c=c,
        r=r,
        avg=None,
        raw_slot_type=coefficient_type,
        raw_slot_a=a,
        raw_slot_b=b,
        raw_slot_c=c,
        raw_slot_r=r,
        raw_slot_avg=None,
        raw_coef=None,
        coef_types=None,
        coef_description=None,
        raw_description=None,
        raw_tooltip=None,
    )


def test_exact_uesp_empty_slot_marker_is_inactive():
    assert not is_active_coefficient(
        _row(coefficient_type="-1", a=-1.0, b=-1.0, c=-1.0, r=-1.0)
    )


def test_other_negative_coefficient_data_is_not_silently_discarded():
    assert is_active_coefficient(
        _row(coefficient_type="-1", a=0.0, b=-1.0, c=-1.0, r=-1.0)
    )


def test_component_semantics_audit_can_be_launched_as_a_script():
    script = ROOT / "tools" / "audit_skill_component_text_semantics.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Audit explicit per-coefficient semantics" in completed.stdout
