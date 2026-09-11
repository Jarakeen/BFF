from pathlib import Path
from types import SimpleNamespace

import pytest

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from tools.audit_phase13_saved_build_stabilized_healer_output import (
    _full_fight_demand,
    _print_healing_evidence,
    _runtime_mode_label,
)


def test_full_fight_demand_covers_entire_stabilized_plan_window():
    demand = _full_fight_demand(60.0)

    assert demand.name == "full stabilized healer-output audit"
    assert demand.start_seconds == pytest.approx(0.0)
    assert demand.end_seconds == pytest.approx(60.0)
    assert demand.kind is RotationDemandKind.HEALING
    assert demand.pattern is RotationDemandPattern.SUSTAINED
    assert demand.target_count == 12


def test_full_fight_demand_rejects_nonpositive_duration():
    with pytest.raises(ValueError, match="duration must be positive"):
        _full_fight_demand(0.0)


def test_runtime_mode_label_distinguishes_static_fallback_from_explicit_history():
    assert _runtime_mode_label(None).startswith("STATIC FALLBACK")
    assert _runtime_mode_label(Path("runtime.json")).startswith(
        "EXACT-TIME RUNTIME HISTORY"
    )


def test_print_healing_evidence_reports_all_temporal_classes(capsys):
    evidence = SimpleNamespace(
        direct_events=(object(),),
        periodic_events=(object(), object()),
        delayed_events=(object(),),
        channel_events=(object(), object(), object()),
        modeled_direct_healing=100.0,
        modeled_periodic_healing=200.0,
        modeled_delayed_healing=300.0,
        modeled_channel_healing=400.0,
        modeled_external_conditional_healing=50.0,
        modeled_total_healing=1050.0,
        unresolved=("missing reviewed cadence",),
    )

    _print_healing_evidence(evidence)
    output = capsys.readouterr().out

    assert "Direct events:" in output
    assert "Periodic events:" in output
    assert "Delayed events:" in output
    assert "Channel events:" in output
    assert "External conditional:" in output
    assert "Modeled total:" in output
    assert "missing reviewed cadence" in output
