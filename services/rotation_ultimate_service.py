from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from minmax.rotation_ultimate import UltimateRotationScheduler, UltimateScheduleRule
from minmax.ultimate_resource_timeline import (
    UltimateGenerationEvent,
    UltimateResourceProjection,
    UltimateResourceTimeline,
    UltimateSpendRule,
)


@dataclass(frozen=True)
class RotationUltimateProjection:
    plan: RotationPlan
    rules: tuple[UltimateScheduleRule, ...]
    unresolved: tuple[str, ...]
    resource_projections: tuple[tuple[str, UltimateResourceProjection], ...] = ()


class RotationUltimateService:
    """Resolve saved ultimates and apply explicit Ultimate timing evidence.

    Callers may either supply already-resolved availability times through
    ``apply`` or explicit starting Ultimate plus gain events through
    ``apply_generation``. Neither path invents Ultimate generation.
    """

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        ability_cost_repository: AbilityCostRepository | None = None,
        scheduler: UltimateRotationScheduler | None = None,
        resource_timeline: UltimateResourceTimeline | None = None,
    ) -> None:
        self.ability_cost_repository = ability_cost_repository or AbilityCostRepository(
            database_path
        )
        self.scheduler = scheduler or UltimateRotationScheduler()
        self.resource_timeline = resource_timeline or UltimateResourceTimeline()

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

        for bar, values in self._bar_skill_values(build):
            ultimate = self._slot_six(values)
            if not ultimate:
                continue

            times = availability.get(bar, ())
            if not times:
                unresolved.append(
                    f"saved {bar}-bar ultimate '{ultimate}' is not scheduled because no explicit Ultimate availability evidence was supplied"
                )
                continue

            resolved = self._resolve_ultimate_rule(
                ultimate=ultimate,
                bar=bar,
                available_at_seconds=times,
                unresolved=unresolved,
            )
            if resolved is not None:
                rules.append(resolved)

        return self._finish(
            plan=plan,
            rules=tuple(rules),
            unresolved=tuple(unresolved),
        )

    def apply_generation(
        self,
        *,
        build,
        plan: RotationPlan,
        starting_ultimate_by_bar: dict[str, float] | None = None,
        generation_events_by_bar: dict[str, tuple[UltimateGenerationEvent, ...]] | None = None,
    ) -> RotationUltimateProjection:
        """Derive ultimate affordability from explicit generation evidence.

        The saved slot-6 ability supplies identity. Canonical ability-cost evidence
        supplies cost. The caller supplies starting Ultimate and generation events.
        This service then computes affordability times and feeds them to the same
        deterministic ultimate scheduler used by ``apply``.
        """
        starting = {
            str(bar).strip().casefold(): float(value)
            for bar, value in (starting_ultimate_by_bar or {}).items()
        }
        events_by_bar = {
            str(bar).strip().casefold(): tuple(events)
            for bar, events in (generation_events_by_bar or {}).items()
        }

        rules: list[UltimateScheduleRule] = []
        projections: list[tuple[str, UltimateResourceProjection]] = []
        unresolved = list(plan.unresolved)

        for bar, values in self._bar_skill_values(build):
            ultimate = self._slot_six(values)
            if not ultimate:
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

            projection = self.resource_timeline.project(
                starting_amount=starting.get(bar, 0.0),
                events=events_by_bar.get(bar, ()),
                spend_rule=UltimateSpendRule(
                    skill_name=resolution.name or ultimate,
                    cost=base_cost.amount,
                ),
                duration_seconds=plan.duration_seconds,
            )
            projections.append((bar, projection))

            if not projection.availability_times:
                unresolved.append(
                    f"saved {bar}-bar ultimate '{ultimate}' never became affordable from the supplied explicit Ultimate timeline"
                )
                continue

            rules.append(
                UltimateScheduleRule(
                    skill_name=resolution.name or ultimate,
                    bar=bar,
                    cost=base_cost.amount,
                    available_at_seconds=projection.availability_times,
                )
            )

        return self._finish(
            plan=plan,
            rules=tuple(rules),
            unresolved=tuple(unresolved),
            resource_projections=tuple(projections),
        )

    def _resolve_ultimate_rule(
        self,
        *,
        ultimate: str,
        bar: str,
        available_at_seconds: tuple[float, ...],
        unresolved: list[str],
    ) -> UltimateScheduleRule | None:
        resolution = self.ability_cost_repository.resolve_name(ultimate)
        unresolved.extend(resolution.unresolved)
        base_cost = resolution.base_cost
        if base_cost is None:
            unresolved.append(
                f"saved {bar}-bar ultimate '{ultimate}' has no resolved canonical cost"
            )
            return None
        if ResourceType.ULTIMATE not in base_cost.resources:
            unresolved.append(
                f"saved slot-6 ability '{ultimate}' resolved without the Ultimate resource mechanic"
            )
            return None
        return UltimateScheduleRule(
            skill_name=resolution.name or ultimate,
            bar=bar,
            cost=base_cost.amount,
            available_at_seconds=available_at_seconds,
        )

    def _finish(
        self,
        *,
        plan: RotationPlan,
        rules: tuple[UltimateScheduleRule, ...],
        unresolved: tuple[str, ...],
        resource_projections: tuple[tuple[str, UltimateResourceProjection], ...] = (),
    ) -> RotationUltimateProjection:
        result = self.scheduler.apply(plan, rules) if rules else plan
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
            rules=rules,
            unresolved=merged,
            resource_projections=resource_projections,
        )

    @staticmethod
    def _bar_skill_values(build):
        return (
            ("front", getattr(build, "FrontBarSkills", [])),
            ("back", getattr(build, "BackBarSkills", [])),
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
