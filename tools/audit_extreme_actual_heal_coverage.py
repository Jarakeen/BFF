from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.extreme_actual_heal_coverage_audit_service import (
    ExtremeActualHealCoverageAuditService,
)


def audit() -> tuple[str, ...]:
    service = ExtremeActualHealCoverageAuditService()
    rows = service.items()
    summary = service.summary()

    lines = [
        "Extreme MOST Actual Heal H1 coverage audit",
        "==========================================",
    ]
    for row in rows:
        lines.append(
            f"[{row.status.upper():11}] {row.category}: {row.mechanic_id}"
        )
        lines.append(f"  evidence: {row.evidence}")
        lines.append(f"  detail:   {row.detail}")

    lines.extend(
        (
            "",
            "Summary",
            "-------",
            f"implemented: {summary.implemented}",
            f"conditional: {summary.conditional}",
            f"unresolved:  {summary.unresolved}",
            f"irrelevant:  {summary.irrelevant}",
            f"coverage:    {summary.covered}/{summary.denominator} "
            f"({summary.coverage_fraction:.1%})",
            "blockers:     " + (", ".join(summary.blocker_ids) or "none"),
        )
    )
    return tuple(lines)


def main() -> int:
    for line in audit():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
