from __future__ import annotations

from dataclasses import dataclass
import re

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationActionKind, RotationPlan


_HORIZON_PATTERN = re.compile(
    r"^skill '(.+)' was displaced beyond the [0-9]+(?:\.[0-9]+)?s plan horizon .* on (front|back) bar$",
    re.IGNORECASE,
)
_REFRESH_DISPLACEMENT_PATTERN = re.compile(
    r"^refresh obligation for '.+' claimed the ([0-9]+(?:\.[0-9]+)?)s (front|back)-bar slot from '(.+)'; displaced skill will cascade to the next same-bar skill slot$",
    re.IGNORECASE,
)
_CHANNEL_DISPLACEMENT_PATTERN = re.compile(
    r"^(?:skill|ultimate) '(.+)' at ([0-9]+(?:\.[0-9]+)?)s was displaced by a verified channel reservation .* on (front|back) bar$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RotationPriorityHorizonDisplacement:
    bar: str
    skill_name: str
    priority: int
    displaced_from_time_seconds: float | None


@dataclass(frozen=True)
class RotationPriorityDisplacementInversion:
    bar: str
    displaced_skill_name: str
    displaced_priority: int
    displaced_from_time_seconds: float
    lower_priority_skill_name: str
    lower_priority: int
    lower_priority_last_time_seconds: float


@dataclass(frozen=True)
class RotationPriorityDisplacementAudit:
    displaced_beyond_horizon: tuple[RotationPriorityHorizonDisplacement, ...]
    inversions: tuple[RotationPriorityDisplacementInversion, ...]

    @property
    def priority_consistent(self) -> bool:
        return not self.inversions


class RotationPriorityDisplacementAuditService:
    """Detect time-valid displacement outcomes that contradict explicit priority.

    A fixed-horizon plan may legitimately leave actions beyond its end. Horizon
    spillover alone is therefore not a defect. An inversion is reported only when
    the scheduler provides evidence for when the higher-priority action first entered
    the displacement queue and a lower-priority ordinary skill on the same bar was
    still scheduled *after* that point.

    Historical casts before displacement do not count. If the plan says that a skill
    fell beyond the horizon but provides no displacement-start evidence, the audit
    fails closed and records the spillover without inventing an inversion.

    The service is diagnostic only. It does not mutate cadence, refresh timing, bar
    routing, or the displacement queue.
    """

    def audit(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList,
    ) -> RotationPriorityDisplacementAudit:
        resolved_priorities = tuple(priorities.resolve())
        priority_by_key = {
            (item.entry.skill_name.casefold(), item.entry.bar): int(item.effective_priority)
            for item in resolved_priorities
        }
        display_name_by_key = {
            (item.entry.skill_name.casefold(), item.entry.bar): item.entry.skill_name
            for item in resolved_priorities
        }

        displaced_from = self._displacement_start_times(plan)
        displaced: list[RotationPriorityHorizonDisplacement] = []
        for raw in plan.unresolved:
            match = _HORIZON_PATTERN.match(str(raw or "").strip())
            if match is None:
                continue
            skill_name = match.group(1).strip()
            bar = match.group(2).casefold()
            key = (skill_name.casefold(), bar)
            priority = priority_by_key.get(key)
            if priority is None:
                continue
            displaced.append(
                RotationPriorityHorizonDisplacement(
                    bar=bar,
                    skill_name=skill_name,
                    priority=priority,
                    displaced_from_time_seconds=displaced_from.get(key),
                )
            )

        skill_times: dict[tuple[str, str], list[float]] = {}
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            bar = str(action.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                continue
            key = (action.name.casefold(), bar)
            skill_times.setdefault(key, []).append(float(action.time_seconds))

        inversions: list[RotationPriorityDisplacementInversion] = []
        for displacement in displaced:
            displaced_from_time = displacement.displaced_from_time_seconds
            if displaced_from_time is None:
                continue
            for (skill_key, skill_bar), times in skill_times.items():
                if skill_bar != displacement.bar:
                    continue
                lower_priority = priority_by_key.get((skill_key, skill_bar))
                if lower_priority is None or lower_priority <= displacement.priority:
                    continue
                later_times = [value for value in times if value > displaced_from_time]
                if not later_times:
                    continue
                inversions.append(
                    RotationPriorityDisplacementInversion(
                        bar=displacement.bar,
                        displaced_skill_name=displacement.skill_name,
                        displaced_priority=displacement.priority,
                        displaced_from_time_seconds=displaced_from_time,
                        lower_priority_skill_name=display_name_by_key.get(
                            (skill_key, skill_bar), skill_key
                        ),
                        lower_priority=lower_priority,
                        lower_priority_last_time_seconds=max(later_times),
                    )
                )

        inversions.sort(
            key=lambda row: (
                row.bar,
                row.displaced_priority,
                row.displaced_skill_name.casefold(),
                row.displaced_from_time_seconds,
                -row.lower_priority,
                row.lower_priority_skill_name.casefold(),
            )
        )
        displaced.sort(
            key=lambda row: (row.bar, row.priority, row.skill_name.casefold())
        )
        return RotationPriorityDisplacementAudit(
            displaced_beyond_horizon=tuple(displaced),
            inversions=tuple(inversions),
        )

    @staticmethod
    def _displacement_start_times(
        plan: RotationPlan,
    ) -> dict[tuple[str, str], float]:
        result: dict[tuple[str, str], float] = {}
        for raw in plan.unresolved:
            text = str(raw or "").strip()
            refresh = _REFRESH_DISPLACEMENT_PATTERN.match(text)
            if refresh is not None:
                time_seconds = float(refresh.group(1))
                bar = refresh.group(2).casefold()
                skill_name = refresh.group(3).strip()
                key = (skill_name.casefold(), bar)
                result[key] = min(result.get(key, time_seconds), time_seconds)
                continue

            channel = _CHANNEL_DISPLACEMENT_PATTERN.match(text)
            if channel is not None:
                skill_name = channel.group(1).strip()
                time_seconds = float(channel.group(2))
                bar = channel.group(3).casefold()
                key = (skill_name.casefold(), bar)
                result[key] = min(result.get(key, time_seconds), time_seconds)
        return result


__all__ = [
    "RotationPriorityDisplacementAudit",
    "RotationPriorityDisplacementAuditService",
    "RotationPriorityDisplacementInversion",
    "RotationPriorityHorizonDisplacement",
]
