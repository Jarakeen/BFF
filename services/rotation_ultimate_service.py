from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from minmax.rotation_ultimate import UltimateRotationScheduler, UltimateScheduleRule


@dataclass(frozen=True)
class RotationUltimateProjection:
    plan: RotationPlan
    rules: tuple[UltimateScheduleRule, ...]
    unresolved: tuple[str, ...]


class RotationUltimateService:
    """Resolve saved ultimates and apply only explicit availability evidence."""

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        ability_cost_repository: AbilityCostRepository | None = None,
        scheduler: UltimateRotationScheduler | None = None,
    ) -> None:
        self.ability_cost_repository = ability_cost_repository or AbilityCostRepository(
            database_path
        )
        self.scheduler = scheduler or UltimateRotationScheduler()

    def apply(
        self,
        *,
        build,
        plan: RotationPlan,
        availability_by_bar: dict[str, tuple[float, ...]] | None = None,
    ) -> RotationUltimateProjection:
        availability = {
            str(bar).strip().casefold(): tuple(times)
            for bar, times in (availability_by_bar or {}).items()
        }
        rules: list[UltimateScheduleRule] = []
        unresolved = list(plan.unresolved)

        for bar, values in (
            ("front", getattr(build, "FrontBarSkills", [])),
            ("back", getattr(build, "BackBarSkills", [])),
        ):
            ultimate = self._slot_six(values)
            if not ultimate:
                continue

            times = availability.get(bar, ())
            if not times:
                unresolved.append(
                    f"saved {bar}-bar ultimate '{ultimate}' is not scheduled because no explicit Ultimate availability evidence was supplied"
                )
                continue

            resolution = self.ability_cost_repository.resolve_name(ultimate)
            unresolved.extend(resolution.unresolved)
            base_cost = resolution.base_cost
            if base_cost is None:
                unresolved.append(
                    f"saved {bar}-bar ultimate '{ultimate}' has no resolved canonical cost"
                )
                continue
            if ResourceType.ULTIMATE not in base_cost.resources:
                unresolved.append(
                    f"saved slot-6 ability '{ultimate}' resolved without the Ultimate resource mechanic"
                )
                continue

            rules.append(
                UltimateScheduleRule(
                    skill_name=resolution.name or ultimate,
                    bar=bar,
                    cost=base_cost.amount,
                    available_at_seconds=times,
                )
            )

        result = self.scheduler.apply(plan, tuple(rules)) if rules else plan
        merged = self._dedupe(tuple(result.unresolved) + tuple(unresolved))
        if merged != result.unresolved:
            result = RotationPlan(
                character_name=result.character_name,
                build_name=result.build_name,
                duration_seconds=result.duration_seconds,
                actions=result.actions,
                assumptions=result.assumptions,
                unresolved=merged,
            )

        return RotationUltimateProjection(
            plan=result,
            rules=tuple(rules),
            unresolved=merged,
        )

    @staticmethod
    def _slot_six(values) -> str:
        skills = list(values or [])
        if len(skills) < 6:
            return ""
        return str(skills[5] or "").strip()

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)
