from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from minmax.rotation_ultimate import UltimateRotationScheduler, UltimateScheduleRule
from minmax.secondary_ultimate_activation_repository import (
    SecondaryUltimateActivationRepository,
)
from minmax.ultimate_generation_sources import (
    CombatAttackUltimateGenerationSource,
    HeroismUltimateGenerationSource,
    HeroismWindow,
)
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


@dataclass(frozen=True)
class _ResolvedUltimateSpend:
    skill_name: str
    cost: float
    unresolved: tuple[str, ...] = ()


class RotationUltimateService:
    """Resolve saved ultimates and apply explicit Ultimate timing evidence.

    Normal one-shot Ultimates resolve from canonical ``ability.base_cost``.
    Persistent/summoned Ultimates may instead expose an explicitly described
    secondary activation with its own Ultimate cost. Those are resolved through
    ``SecondaryUltimateActivationRepository`` without rewriting the slotted
    ability's zero base cost.
    """

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        ability_cost_repository: AbilityCostRepository | None = None,
        secondary_activation_repository: SecondaryUltimateActivationRepository | None = None,
        scheduler: UltimateRotationScheduler | None = None,
        resource_timeline: UltimateResourceTimeline | None = None,
        heroism_source: HeroismUltimateGenerationSource | None = None,
        combat_attack_source: CombatAttackUltimateGenerationSource | None = None,
    ) -> None:
        self.ability_cost_repository = ability_cost_repository or AbilityCostRepository(
            database_path
        )
        self.secondary_activation_repository = (
            secondary_activation_repository
            or SecondaryUltimateActivationRepository(database_path)
        )
        self.scheduler = scheduler or UltimateRotationScheduler()
        self.resource_timeline = resource_timeline or UltimateResourceTimeline()
        self.heroism_source = heroism_source or HeroismUltimateGenerationSource()
        self.combat_attack_source = combat_attack_source or CombatAttackUltimateGenerationSource()

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
        ultimate_bar: str,
        starting_ultimate: float = 0.0,
        generation_events: tuple[UltimateGenerationEvent, ...] = (),
        heroism_windows: tuple[HeroismWindow, ...] = (),
        use_scheduled_combat_attacks: bool = False,
    ) -> RotationUltimateProjection:
        """Derive affordability from one shared Ultimate resource pool."""
        bar = str(ultimate_bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("ultimate generation projection requires 'front' or 'back' ultimate_bar")

        values = (
            getattr(build, "FrontBarSkills", [])
            if bar == "front"
            else getattr(build, "BackBarSkills", [])
        )
        ultimate = self._slot_six(values)
        unresolved = list(plan.unresolved)
        if not ultimate:
            unresolved.append(f"saved build has no {bar}-bar slot-6 ultimate to project")
            return self._finish(
                plan=plan,
                rules=(),
                unresolved=tuple(unresolved),
            )

        spend = self._resolve_ultimate_spend(ultimate)
        unresolved.extend(spend.unresolved)
        if spend.cost <= 0:
            unresolved.append(
                f"saved {bar}-bar ultimate '{ultimate}' has no resolved canonical spend"
            )
            return self._finish(plan=plan, rules=(), unresolved=tuple(unresolved))

        heroism_events = self.heroism_source.events(
            windows=tuple(heroism_windows),
            duration_seconds=plan.duration_seconds,
        )
        combat_events = self.combat_attack_source.events_from_plan(
            plan=plan,
            assume_scheduled_attacks_damage=bool(use_scheduled_combat_attacks),
        )
        all_events = (
            tuple(generation_events)
            + tuple(heroism_events)
            + tuple(combat_events)
        )

        projection = self.resource_timeline.project(
            starting_amount=starting_ultimate,
            events=all_events,
            spend_rule=UltimateSpendRule(
                skill_name=spend.skill_name,
                cost=spend.cost,
            ),
            duration_seconds=plan.duration_seconds,
        )

        if not projection.availability_times:
            unresolved.append(
                f"saved {bar}-bar ultimate '{ultimate}' never became affordable from the supplied Ultimate generation evidence"
            )
            rules: tuple[UltimateScheduleRule, ...] = ()
        else:
            rules = (
                UltimateScheduleRule(
                    skill_name=spend.skill_name,
                    bar=bar,
                    cost=spend.cost,
                    available_at_seconds=projection.availability_times,
                ),
            )

        other_bar = "back" if bar == "front" else "front"
        other_values = (
            getattr(build, "BackBarSkills", [])
            if other_bar == "back"
            else getattr(build, "FrontBarSkills", [])
        )
        other_ultimate = self._slot_six(other_values)
        if other_ultimate:
            unresolved.append(
                f"shared Ultimate projection selected {bar}-bar '{ultimate}'; competing {other_bar}-bar ultimate '{other_ultimate}' choice policy is unresolved"
            )

        return self._finish(
            plan=plan,
            rules=rules,
            unresolved=tuple(unresolved),
            resource_projections=((bar, projection),),
        )

    def _resolve_ultimate_spend(self, ultimate: str) -> _ResolvedUltimateSpend:
        resolution = self.ability_cost_repository.resolve_name(ultimate)
        base_cost = resolution.base_cost
        if base_cost is not None:
            if ResourceType.ULTIMATE not in base_cost.resources:
                return _ResolvedUltimateSpend(
                    skill_name=resolution.name or ultimate,
                    cost=0.0,
                    unresolved=tuple(resolution.unresolved)
                    + (
                        f"saved slot-6 ability '{ultimate}' resolved without the Ultimate resource mechanic",
                    ),
                )
            return _ResolvedUltimateSpend(
                skill_name=resolution.name or ultimate,
                cost=float(base_cost.amount),
                unresolved=tuple(resolution.unresolved),
            )

        secondary = self.secondary_activation_repository.resolve_name(ultimate)
        activation = secondary.activation
        if activation is not None:
            retained = tuple(
                item
                for item in resolution.unresolved
                if "no positive canonical base cost" not in str(item).casefold()
            )
            return _ResolvedUltimateSpend(
                skill_name=activation.activation_name,
                cost=float(activation.cost),
                unresolved=retained,
            )

        return _ResolvedUltimateSpend(
            skill_name=resolution.name or ultimate,
            cost=0.0,
            unresolved=tuple(resolution.unresolved) + tuple(secondary.unresolved),
        )

    def _resolve_ultimate_rule(
        self,
        *,
        ultimate: str,
        bar: str,
        available_at_seconds: tuple[float, ...],
        unresolved: list[str],
    ) -> UltimateScheduleRule | None:
        spend = self._resolve_ultimate_spend(ultimate)
        unresolved.extend(spend.unresolved)
        if spend.cost <= 0:
            unresolved.append(
                f"saved {bar}-bar ultimate '{ultimate}' has no resolved canonical spend"
            )
            return None
        return UltimateScheduleRule(
            skill_name=spend.skill_name,
            bar=bar,
            cost=spend.cost,
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
