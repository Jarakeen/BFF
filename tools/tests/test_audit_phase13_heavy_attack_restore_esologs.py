from types import SimpleNamespace

from tools.audit_phase13_heavy_attack_restore_esologs import _amount_summary


def test_amount_summary_ranks_frequency_then_amount():
    observations = (
        SimpleNamespace(resource_change=2900.0),
        SimpleNamespace(resource_change=2823.0),
        SimpleNamespace(resource_change=2900.0),
        SimpleNamespace(resource_change=3000.0),
        SimpleNamespace(resource_change=2823.0),
        SimpleNamespace(resource_change=2900.0),
    )

    assert _amount_summary(observations) == (
        (2900.0, 3),
        (2823.0, 2),
        (3000.0, 1),
    )
