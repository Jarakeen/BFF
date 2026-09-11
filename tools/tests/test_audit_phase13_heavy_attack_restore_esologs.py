from types import SimpleNamespace

from tools.audit_phase13_heavy_attack_restore_esologs import (
    _amount_summary,
    _print_alias_candidates,
)


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


def test_print_alias_candidates_preserves_raw_alias_and_resource_evidence(capsys):
    rows = (
        SimpleNamespace(
            event_count=12,
            source_id=42,
            ability_name="Frost Staff Heavy Attack",
            ability_game_id=101,
            resource_change_type=9,
            minimum_restore=2823.0,
            maximum_restore=2900.0,
        ),
    )

    _print_alias_candidates(rows, limit=10)
    output = capsys.readouterr().out

    assert "Frost Staff Heavy Attack" in output
    assert "[101]" in output
    assert "resource_type=9" in output
    assert "restore_range=2823..2900" in output
