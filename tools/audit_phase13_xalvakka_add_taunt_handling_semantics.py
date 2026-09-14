from __future__ import annotations

"""Audit reviewed Xalvakka actor-specific add-taunt handling semantics."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_tank_encounter_add_taunt_handling_service import (
    RotationTankEncounterAddTauntHandlingService,
)


def audit() -> tuple[str, ...]:
    reviewed = RotationTankEncounterAddTauntHandlingService().reviewed_for("xalvakka_hm")
    if reviewed is None:
        return ("UNRESOLVED=no reviewed Xalvakka add-taunt handling semantics",)

    lines = [
        "PHASE 13 XALVAKKA ADD TAUNT HANDLING SEMANTICS AUDIT",
        f"EVIDENCE_SCOPE={reviewed.evidence_scope}",
        f"SOURCE_REPORT={reviewed.source_report}",
        f"ACTIVE_WINDOW={reviewed.active_window_semantics}",
        f"TAUNT_STATE={reviewed.taunt_state_semantics}",
    ]
    for actor in reviewed.actors:
        lines.append(
            f"ACTOR: {actor.actor_name} handling={actor.handling_class} "
            f"observed={actor.observed_instances} untaunted={actor.untaunted_instances} "
            f"multi_source={actor.multi_source_instances} median_coverage={actor.median_coverage_fraction * 100.0:.1f}% "
            f"range={actor.minimum_coverage_fraction * 100.0:.1f}-{actor.maximum_coverage_fraction * 100.0:.1f}% "
            f"ranking_context={actor.ranking_context} hard_maintenance_policy={actor.hard_maintenance_policy}"
        )
    lines.extend(
        (
            "STATUS=ACTOR_SPECIFIC_REVIEWED_BEHAVIOR",
            "HARD_UPTIME_FLOOR=BLOCKED",
            "INTERPRETATION=Iron Atronach is a strong taunt-maintenance target while Daedroth taunt is selective/contextual in the reviewed report; no exact universal uptime threshold is promoted",
        )
    )
    return tuple(lines)


def main() -> int:
    for line in audit():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
