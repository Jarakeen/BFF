from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.audit_phase13_xalvakka_healer_lead_boundary import (
    _generate_legal_candidates,
    _lead_from_candidate_id,
    _lead_grid,
)


def test_lead_grid_includes_fractional_stop_without_float_drift() -> None:
    assert _lead_grid(1.0, 3.0, 0.5) == (1.0, 1.5, 2.0, 2.5, 3.0)


def test_lead_grid_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="start-seconds must be positive"):
        _lead_grid(0.0, 3.0, 0.5)
    with pytest.raises(ValueError, match="stop-seconds must be greater"):
        _lead_grid(3.0, 2.0, 0.5)
    with pytest.raises(ValueError, match="step-seconds must be positive"):
        _lead_grid(1.0, 3.0, 0.0)


def test_lead_candidate_id_parser_preserves_baseline_boundary() -> None:
    assert _lead_from_candidate_id("seeds-7.5s-early") == 7.5
    assert _lead_from_candidate_id("baseline") is None
    assert _lead_from_candidate_id("demand-aware-0s") is None
    assert _lead_from_candidate_id("seeds-not-a-number-s-early") is None


def test_legal_candidate_generation_keeps_valid_options_when_one_exceeds_rule() -> None:
    class FakeGenerator:
        def generate(self, *, options, baseline_id, **_kwargs):
            baseline = SimpleNamespace(candidate_id=baseline_id)
            if not options:
                return (baseline,)
            option = options[0]
            if option.option_id == "seeds-4s-early":
                raise ValueError(
                    "demand refresh lead must remain shorter than the verified ordinary refresh span for Budding Seeds"
                )
            return (baseline, SimpleNamespace(candidate_id=option.option_id))

    options = (
        SimpleNamespace(option_id="seeds-2s-early"),
        SimpleNamespace(option_id="seeds-4s-early"),
        SimpleNamespace(option_id="seeds-3s-early"),
    )
    generated, rejected = _generate_legal_candidates(
        FakeGenerator(),
        seed_plan=object(),
        priorities=object(),
        demand=object(),
        options=options,
    )

    assert tuple(item.candidate_id for item in generated) == (
        "demand-aware-0s",
        "seeds-2s-early",
        "seeds-3s-early",
    )
    assert rejected == (
        (
            "seeds-4s-early",
            "demand refresh lead must remain shorter than the verified ordinary refresh span for Budding Seeds",
        ),
    )
