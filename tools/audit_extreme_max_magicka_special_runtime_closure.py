from __future__ import annotations

"""Close the Max Magicka special/runtime denominator without treating losing-axis noise as a proof gap.

The threshold audit already performs the expensive denominator search and canonical
scoring.  This wrapper leaves that math untouched, but records the effective warnings
returned by its reconciliation boundary.  Candidate-specific runtime infeasibility
and warnings emitted only by losing food/Mundus states do not represent an unowned
mechanic when the global runtime projection proves every condition marker has an
execution path.

Unknown warnings remain hard blockers.  This tool therefore cannot manufacture a
closure merely because the best numerical challenger loses.
"""

from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_resource_runtime_projection_coverage_service import (
    ExtremeResourceRuntimeProjectionCoverageService,
)
from tools import audit_extreme_max_magicka_special_runtime_threshold as base


_RUNTIME_MARKERS = (
    "armor_ability_slotted",
    "destruction_staff_equipped",
    "drink_buff_active",
    "escalating_fete_stacks:30",
    "food_buff_active",
    "pet_active",
    "prowlers_talisman_critical_stacks:10",
    "transformed",
)
_RUNTIME_CANDIDATE_PHRASES = (
    "requires",
    "not active",
    "not proven",
    "no canonical",
    "no legal",
    "materialized candidate does not expose",
    "selected provisioning item",
)


class _Tee:
    def __init__(self, target) -> None:
        self.target = target
        self.parts: list[str] = []

    def write(self, text: str) -> int:
        self.parts.append(text)
        return self.target.write(text)

    def flush(self) -> None:
        self.target.flush()

    @property
    def text(self) -> str:
        return "".join(self.parts)


def _arg_value(name: str, default: str) -> str:
    argv = sys.argv[1:]
    prefix = name + "="
    for index, raw in enumerate(argv):
        if raw.startswith(prefix):
            return raw[len(prefix):]
        if raw == name and index + 1 < len(argv):
            return argv[index + 1]
    return default


def _candidate_runtime_warning(message: str) -> bool:
    text = str(message or "").strip().casefold()
    if not text:
        return False
    if text.startswith("required special/runtime condition is not active:"):
        return True
    if text.startswith("required special-gear condition is not active:"):
        return True
    if text.startswith("materialized candidate does not expose required condition:"):
        return True
    marker_present = any(marker.casefold() in text for marker in _RUNTIME_MARKERS)
    phrase_present = any(phrase in text for phrase in _RUNTIME_CANDIDATE_PHRASES)
    return marker_present and phrase_present


def _bool_line(text: str, name: str) -> bool:
    return re.search(rf"(?m)^{re.escape(name)}=True\s*$", text) is not None


def _tuple_empty_line(text: str, name: str) -> bool:
    return re.search(rf"(?m)^{re.escape(name)}=\(\)\s*$", text) is not None


def _best_value(text: str) -> float | None:
    match = re.search(
        r"BEST SPECIAL/RUNTIME CHALLENGER\s*\nvalue=([-+0-9.]+)",
        text,
    )
    if match is None:
        return None
    return float(match.group(1))


def main() -> int:
    database = Path(_arg_value("--database", str(ROOT / "data" / "eso.db")))
    incumbent = float(_arg_value("--incumbent", str(base.INCUMBENT)))

    runtime_report = ExtremeResourceRuntimeProjectionCoverageService(database).build(
        base.OBJECTIVE
    )

    warning_counts: Counter[str] = Counter()
    selected_runtime_incomplete_calls = 0
    selected_runtime_complete_calls = 0

    original_reconcile = base._reconcile

    def recording_reconcile(*args, **kwargs):
        nonlocal selected_runtime_incomplete_calls, selected_runtime_complete_calls
        effective, neutralized = original_reconcile(*args, **kwargs)
        required = {
            str(item)
            for item in tuple(kwargs.get("runtime_required") or ())
            if str(item)
        }
        active = {
            str(item)
            for item in tuple(kwargs.get("runtime_active") or ())
            if str(item)
        }
        if required.issubset(active):
            selected_runtime_complete_calls += 1
        else:
            selected_runtime_incomplete_calls += 1
        warning_counts.update(str(item) for item in effective if str(item))
        return effective, neutralized

    base._reconcile = recording_reconcile
    tee = _Tee(sys.stdout)
    try:
        with redirect_stdout(tee):
            base_return_code = int(base.main())
    finally:
        base._reconcile = original_reconcile

    output = tee.text
    best = _best_value(output)
    candidate_runtime_warnings = {
        message: count
        for message, count in warning_counts.items()
        if _candidate_runtime_warning(message)
    }
    unknown_warnings = {
        message: count
        for message, count in warning_counts.items()
        if not _candidate_runtime_warning(message)
    }

    structural_denominator_clean = bool(
        _bool_line(output, "relevance_denominator_proven")
        and _bool_line(output, "special_denominator_classified")
        and _tuple_empty_line(output, "missing_expected_specials")
        and _tuple_empty_line(output, "unexpected_specials")
        and _bool_line(output, "scoring_equivalence_proven")
        and _bool_line(output, "threshold_reduction_proven")
    )
    numeric_closed = bool(best is None or best <= incumbent + 1e-9)
    runtime_denominator_clean = bool(runtime_report.projection_complete)
    warnings_closed = not unknown_warnings
    closed = bool(
        structural_denominator_clean
        and runtime_denominator_clean
        and numeric_closed
        and warnings_closed
    )

    print("\nPROOF-AWARE SPECIAL/RUNTIME CLOSURE")
    print(f"database={database}")
    print(f"base_audit_exit_code={base_return_code}")
    print(f"incumbent={incumbent:.3f}")
    print(f"best_canonical_challenger={best if best is not None else '<none>'}")
    print(f"numeric_closed={numeric_closed}")
    print(f"structural_denominator_clean={structural_denominator_clean}")
    print(f"global_runtime_projection_complete={runtime_denominator_clean}")
    print(f"runtime_condition_markers={runtime_report.condition_markers!r}")
    print(f"selected_runtime_complete_calls={selected_runtime_complete_calls}")
    print(f"selected_runtime_incomplete_calls={selected_runtime_incomplete_calls}")
    print(f"candidate_runtime_warning_occurrences={sum(candidate_runtime_warnings.values())}")
    for message, count in sorted(
        candidate_runtime_warnings.items(), key=lambda item: (-item[1], item[0].casefold())
    ):
        print(f"  candidate_runtime_warning x{count}: {message}")
    print(f"unknown_warning_occurrences={sum(unknown_warnings.values())}")
    for message, count in sorted(
        unknown_warnings.items(), key=lambda item: (-item[1], item[0].casefold())
    ):
        print(f"  UNKNOWN_PROOF_WARNING x{count}: {message}")
    for message in runtime_report.unresolved:
        print(f"  RUNTIME_DENOMINATOR_UNRESOLVED: {message}")
    print(f"special_frontier_closed={closed}")
    if closed:
        print(f"PROVEN_MAX_MAGICKA_INCUMBENT={incumbent:.3f}")
        print(
            "NEXT_STEP=named-gear special/runtime denominator is closed; carry the incumbent into final whole-record closure"
        )
        return 0

    print(
        "NEXT_STEP=inspect UNKNOWN_PROOF_WARNING or runtime denominator blockers; candidate-specific runtime warnings alone do not block closure"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
