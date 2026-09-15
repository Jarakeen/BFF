from __future__ import annotations

from types import SimpleNamespace

from services.extreme_actual_heal_armor_weight_package_adapter import (
    ExtremeActualHealArmorWeightPackageAdapter,
)


class _Delegate:
    def __init__(self, candidates):
        self.candidates = tuple(candidates)
        self.calls = []
        self.specialist_value = "preserved"

    def build_candidates(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.candidates


class _ArmorWeights:
    def __init__(self, results):
        self.results = dict(results)
        self.calls = []

    def expand_candidate(self, candidate):
        self.calls.append(candidate)
        return self.results[candidate.candidate_id]


def _candidate(name):
    return SimpleNamespace(candidate_id=name)


def _result(*candidates, proven=True, unresolved=(), raw=3, retained=2):
    return SimpleNamespace(
        candidates=tuple(candidates),
        denominator_proven=proven,
        unresolved=tuple(unresolved),
        raw_layout_count=raw,
        retained_signature_count=retained,
    )


def test_package_adapter_expands_every_candidate_and_reports_denominator_stats():
    first = _candidate("first")
    second = _candidate("second")
    first_a = _candidate("first:a")
    first_b = _candidate("first:b")
    second_a = _candidate("second:a")
    delegate = _Delegate((first, second))
    armor = _ArmorWeights(
        {
            "first": _result(first_a, first_b, raw=9, retained=2),
            "second": _result(second_a, raw=3, retained=1),
        }
    )
    service = ExtremeActualHealArmorWeightPackageAdapter(
        delegate,
        armor,
        label="five-piece",
    )

    result = service.build_candidates("build", character_id="char")

    assert result == (first_a, first_b, second_a)
    assert len(delegate.calls) == 1
    assert armor.calls == [first, second]
    assert service.stats.raw_package_candidates == 2
    assert service.stats.expanded_candidates == 3
    assert service.stats.raw_weight_layouts_reviewed == 12
    assert service.stats.retained_weight_signatures == 3
    assert service.stats.unresolved == ()


def test_package_adapter_drops_unproven_physical_candidate_but_keeps_blocker():
    candidate = _candidate("illegal")
    delegate = _Delegate((candidate,))
    armor = _ArmorWeights(
        {
            "illegal": _result(
                proven=False,
                unresolved=("canonical armor_type missing",),
                raw=0,
                retained=0,
            )
        }
    )
    service = ExtremeActualHealArmorWeightPackageAdapter(
        delegate,
        armor,
        label="mythic-package",
    )

    result = service.build_candidates()

    assert result == ()
    assert service.stats.unresolved == (
        "mythic-package | illegal: canonical armor_type missing",
    )


def test_package_adapter_reset_clears_previous_diagnostics():
    candidate = _candidate("candidate")
    service = ExtremeActualHealArmorWeightPackageAdapter(
        _Delegate((candidate,)),
        _ArmorWeights({"candidate": _result(candidate)}),
        label="package",
    )

    service.build_candidates()
    assert service.stats.raw_package_candidates == 1

    service.reset()
    assert service.stats.raw_package_candidates == 0
    assert service.stats.unresolved == ()


def test_package_adapter_preserves_specialist_delegate_helpers():
    service = ExtremeActualHealArmorWeightPackageAdapter(
        _Delegate(()),
        _ArmorWeights({}),
        label="package",
    )

    assert service.specialist_value == "preserved"
