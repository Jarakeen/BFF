from __future__ import annotations

"""Audit reviewed Killer's Blade continuous execute amplification semantics."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_reviewed_execute_amplification_service import (
    RotationReviewedExecuteAmplificationService,
)


def main() -> int:
    service = RotationReviewedExecuteAmplificationService()
    samples = (
        (0.50, 1.0),
        (0.375, 2.0),
        (0.25, 3.0),
        (0.125, 4.0),
        (0.0, 5.0),
    )

    print("=" * 72)
    print(" PHASE 13 KILLER'S BLADE EXECUTE AMPLIFICATION AUDIT")
    print("=" * 72)
    passed = True
    for health, expected in samples:
        result = service.resolve_multiplier(
            skill_name="Killer's Blade",
            health_fraction=health,
            threshold=0.50,
            maximum_bonus_fraction=4.0,
        )
        actual = result.damage_multiplier
        ok = actual is not None and abs(float(actual) - expected) <= 1e-9
        passed = passed and ok
        print(
            f"target_health={health * 100:g}% | multiplier="
            f"{actual if actual is not None else 'unresolved'} | expected={expected:g} | "
            f"{'PASS' if ok else 'FAIL'}"
        )
        for item in result.unresolved:
            print(f"  unresolved: {item}")

    unreviewed = service.resolve_multiplier(
        skill_name="Executioner",
        health_fraction=0.25,
        threshold=0.50,
        maximum_bonus_fraction=4.0,
    )
    unreviewed_ok = not unreviewed.resolved and unreviewed.damage_multiplier is None
    passed = passed and unreviewed_ok
    print()
    print(
        "Executioner control | multiplier="
        f"{unreviewed.damage_multiplier if unreviewed.damage_multiplier is not None else 'unresolved'} | "
        f"{'PASS' if unreviewed_ok else 'FAIL'}"
    )
    for item in unreviewed.unresolved:
        print(f"  unresolved: {item}")

    print()
    print(f"RESULT={'PASS' if passed else 'FAIL'}")
    print(
        "Interpretation: Killer's Blade uses only source-reviewed linear missing-Health "
        "scaling; visually similar unreviewed execute tooltips remain fail-closed."
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
