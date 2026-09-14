from __future__ import annotations

from tools.audit_phase13_xalvakka_add_taunt_coverage import Span, _gaps, _merge


def test_merge_unions_overlapping_taunt_spans_without_extending_boundaries():
    merged = _merge(
        (
            Span(1000.0, 5000.0, 1),
            Span(4000.0, 7000.0, 5),
            Span(9000.0, 11000.0, 1),
        ),
        start_ms=2000.0,
        end_ms=10000.0,
    )

    assert tuple((row.start_ms, row.end_ms) for row in merged) == (
        (2000.0, 7000.0),
        (9000.0, 10000.0),
    )


def test_gaps_preserve_leading_internal_and_trailing_untaunted_windows():
    gaps = _gaps(
        (
            Span(3000.0, 5000.0),
            Span(7000.0, 9000.0),
        ),
        start_ms=1000.0,
        end_ms=10000.0,
    )

    assert tuple((row.start_ms, row.end_ms) for row in gaps) == (
        (1000.0, 3000.0),
        (5000.0, 7000.0),
        (9000.0, 10000.0),
    )
