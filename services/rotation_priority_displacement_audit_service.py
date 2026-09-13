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
    r"^refresh obligation for '(.+)' claimed the ([0-9]+(?:\.[0-9]+)?)s (front|back)-bar slot from '(.+)'; displaced skill will cascade to the next same-bar skill slot$",
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
    lower_priority_provenance: str

    @property
    def ordinary_competitor(self) -> bool:
        return self.lower_priority_provenance == "ordinary_or_displaced"


@dataclass(frozen=True)
class RotationPriorityDisplacementAudit:
    displaced_beyond_horizon: tuple[RotationPriorityHorizonDisplacement, ...]
    inversions: tuple[RotationPriorityDisplacementInversion, ...]

    @property
    def ordinary_inversions(self) -> tuple[RotationPriorityDisplacementInversion, ...]:
        return tuple(row for row in self.inversions if row.ordinary_competitor)

    @property
    def priority_consistent(self) -> bool:
        return not self.ordinary_inversions


class RotationPriorityDisplacementAuditService:
    """Detect time-valid displacement outcomes that may contradict explicit priority.

    A fixed-horizon plan may legitimately leave actions beyond its end. Horizon
    spillover alone is therefore not a defect. Candidate inversions are time-scoped:
    the scheduler must provide evidence for when the higher-priority action entered
    the displacement queue and a lower-priority same-bar skill must still be scheduled
    after that point.

    Survivor provenance matters. A lower-priority cast that is itself a due refresh or
    that skill's first cast is protected by the duration scheduler and is not evidence
    that displaced/current priority ordering failed. Only ``ordinary_or_displaced``
    survivors count against ``priority_consistent``. Unknown displacement timing fails
    closed rather than fabricating an inversion.

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
        refresh_claims = self._refresh_claim_times(plan)
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
        for values in skill_times.values():
            values.sort()

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
                last_time = max(later_times)
                first_time = min(times)
                if last_time in refresh_claims.get((skill_key, skill_bar), set()):
                    provenance = "due_refresh"
                elif last_time == first_time:
                    provenance = "first_cast"
                else:
                    provenance = "ordinary_or_displaced"
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
                        lower_priority_last_time_seconds=last_time,
                        lower_priority_provenance=provenance,
                    )
                )

        inversions.sort(
            key=lambda row: (
                row.bar,
                row.displaced_priority,
                row.displaced_skill_name.casefold(),
                row.displaced_from_time_seconds,
                0 if row.ordinary_competitor else 1,
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
    def _refresh_claim_times(
        plan: RotationPlan,
    ) -> dict[tuple[str, str], set[float]]:
        result: dict[tuple[str, str], set[float]] = {}
        for raw in plan.unresolved:
            match = _REFRESH_DISPLACEMENT_PATTERN.match(str(raw or "").strip())
            if match is None:
                continue
            skill_name = match.group(1).strip()
            time_seconds = float(match.group(2))
            bar = match.group(3).casefold()
            result.setdefault((skill_name.casefold(), bar), set()).add(time_seconds)
        return result

    @staticmethod
    def _displacement_start_times(
        plan: RotationPlan,
    ) -> dict[tuple[str, str], float]:
        result: dict[tuple[str, str], float] = {}
        for raw in plan.unresolved:
            text = str(raw or "").strip()
            refresh = _REFRESH_DISPLACEMENT_PATTERN.match(text)
            if refresh is not None:
                time_seconds = float(refresh.group(2))
                bar = refresh.group(3).casefold()
                skill_name = refresh.group(4).strip()
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
