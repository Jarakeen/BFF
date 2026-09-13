from __future__ import annotations

from dataclasses import dataclass
import re

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationActionKind, RotationPlan


_HORIZON_PATTERN = re.compile(
    r"^skill '(.+)' was displaced beyond the [0-9]+(?:\.[0-9]+)?s plan horizon .* on (front|back) bar$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RotationPriorityDisplacementInversion:
    bar: str
    displaced_skill_name: str
    displaced_priority: int
    lower_priority_skill_name: str
    lower_priority: int
    lower_priority_last_time_seconds: float


@dataclass(frozen=True)
class RotationPriorityDisplacementAudit:
    displaced_beyond_horizon: tuple[tuple[str, str, int], ...]
    inversions: tuple[RotationPriorityDisplacementInversion, ...]

    @property
    def priority_consistent(self) -> bool:
        return not self.inversions


class RotationPriorityDisplacementAuditService:
    """Detect FIFO displacement outcomes that contradict explicit ability priority.

    A fixed-horizon plan may legitimately leave actions beyond its end. This audit does
    not treat horizon spillover itself as a defect. It reports only the stronger case:
    a displaced skill with higher explicit priority fell beyond the horizon while a
    lower-priority ordinary skill on the same bar still received a scheduled SKILL slot.

    The service is diagnostic only. It does not mutate cadence, refresh timing, bar
    routing, or the displacement queue.
    """

    def audit(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList,
    ) -> RotationPriorityDisplacementAudit:
        priority_by_key = {
            (item.entry.skill_name.casefold(), item.entry.bar): int(item.effective_priority)
            for item in priorities.resolve()
        }
        displaced: list[tuple[str, str, int]] = []
        for raw in plan.unresolved:
            match = _HORIZON_PATTERN.match(str(raw or "").strip())
            if match is None:
                continue
            skill_name = match.group(1).strip()
            bar = match.group(2).casefold()
            priority = priority_by_key.get((skill_name.casefold(), bar))
            if priority is None:
                continue
            displaced.append((bar, skill_name, priority))

        last_skill_time: dict[tuple[str, str], float] = {}
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            bar = str(action.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                continue
            key = (action.name.casefold(), bar)
            previous = last_skill_time.get(key)
            time_value = float(action.time_seconds)
            if previous is None or time_value > previous:
                last_skill_time[key] = time_value

        inversions: list[RotationPriorityDisplacementInversion] = []
        for bar, displaced_name, displaced_priority in displaced:
            for (skill_key, skill_bar), last_time in last_skill_time.items():
                if skill_bar != bar:
                    continue
                lower_priority = priority_by_key.get((skill_key, skill_bar))
                if lower_priority is None or lower_priority <= displaced_priority:
                    continue
                lower_name = next(
                    (
                        item.entry.skill_name
                        for item in priorities.resolve()
                        if item.entry.bar == skill_bar
                        and item.entry.skill_name.casefold() == skill_key
                    ),
                    skill_key,
                )
                inversions.append(
                    RotationPriorityDisplacementInversion(
                        bar=bar,
                        displaced_skill_name=displaced_name,
                        displaced_priority=displaced_priority,
                        lower_priority_skill_name=lower_name,
                        lower_priority=lower_priority,
                        lower_priority_last_time_seconds=last_time,
                    )
                )

        inversions.sort(
            key=lambda row: (
                row.bar,
                row.displaced_priority,
                row.displaced_skill_name.casefold(),
                -row.lower_priority,
                row.lower_priority_skill_name.casefold(),
            )
        )
        displaced.sort(key=lambda row: (row[0], row[2], row[1].casefold()))
        return RotationPriorityDisplacementAudit(
            displaced_beyond_horizon=tuple(displaced),
            inversions=tuple(inversions),
        )


__all__ = [
    "RotationPriorityDisplacementAudit",
    "RotationPriorityDisplacementAuditService",
    "RotationPriorityDisplacementInversion",
]
