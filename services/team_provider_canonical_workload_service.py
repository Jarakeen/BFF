from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.ability_cost_repository import AbilityCostRepository
from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_final_action_cost import BuildFinalActionCostResolver
from minmax.character_progression import CharacterProgression
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_saved_build_action_slot_service import (
    RotationSavedBuildActionSlotService,
)
from services.rotation_saved_build_action_timing_service import (
    RotationSavedBuildActionTimingService,
)
from services.team_provider_rotation_workload_service import (
    TeamProviderRotationContribution,
    TeamProviderRotationWorkload,
    TeamProviderRotationWorkloadService,
    TeamProviderScheduledActionCost,
)


@dataclass(frozen=True)
class TeamProviderCanonicalActionReference:
    """One provider cast selected from an immutable canonical rotation plan."""

    time_seconds: float
    sequence: int
    primary_role_displacement_seconds: float | None = None

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("provider action time must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_seconds)
        if self.sequence < 0:
            raise ValueError("provider action sequence cannot be negative")
        if self.primary_role_displacement_seconds is not None:
            displacement = float(self.primary_role_displacement_seconds)
            if not isfinite(displacement) or displacement < 0:
                raise ValueError(
                    "primary-role displacement must be finite and non-negative"
                )
            object.__setattr__(
                self,
                "primary_role_displacement_seconds",
                displacement,
            )


@dataclass(frozen=True)
class TeamProviderCanonicalContribution:
    build: PlayerBuild
    progression: CharacterProgression
    plan: RotationPlan
    provider_actions: tuple[TeamProviderCanonicalActionReference, ...]


@dataclass(frozen=True)
class TeamProviderCanonicalWorkloadProjection:
    workload: TeamProviderRotationWorkload
    resolved_contributions: tuple[TeamProviderRotationContribution, ...]


class TeamProviderCanonicalWorkloadService:
    """Resolve provider workload from saved builds and canonical ESO evidence.

    The bridge owns no ESO formulas. It delegates action cost, imported cast/channel
    timing, and saved-build slot ownership to their existing authoritative services,
    then feeds reviewed action evidence into ``TeamProviderRotationWorkloadService``.

    ESO's general global cooldown is not currently canonical database evidence, so
    callers must supply an explicit planning value. Missing GCD policy and missing
    primary-role displacement remain comparison-blocking rather than becoming zero.
    """

    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE,
        *,
        ability_cost_repository: AbilityCostRepository | None = None,
        final_cost_resolver: BuildFinalActionCostResolver | None = None,
        timing_service: RotationSavedBuildActionTimingService | None = None,
        slot_service: RotationSavedBuildActionSlotService | None = None,
        workload_service: TeamProviderRotationWorkloadService | None = None,
    ) -> None:
        self.ability_cost_repository = (
            ability_cost_repository or AbilityCostRepository(database_path)
        )
        self.final_cost_resolver = final_cost_resolver or BuildFinalActionCostResolver(
            BuildActionCostModifierResolver(
                JewelryCostModifierRepository(database_path),
                JewelryTraitRepository(database_path),
            )
        )
        self.timing_service = timing_service or RotationSavedBuildActionTimingService(
            database_path
        )
        self.slot_service = slot_service or RotationSavedBuildActionSlotService()
        self.workload_service = workload_service or TeamProviderRotationWorkloadService()

    def project(
        self,
        *,
        alternative_id: str,
        effect_key: str,
        duration_seconds: float,
        recipient_coverage_met: bool,
        temporal_coverage_met: bool,
        contributions: tuple[TeamProviderCanonicalContribution, ...],
        gcd_seconds_per_application: float | None,
    ) -> TeamProviderCanonicalWorkloadProjection:
        if not contributions:
            raise ValueError("canonical provider workload requires at least one contribution")
        gcd_seconds = self._optional_positive(
            gcd_seconds_per_application,
            field_name="gcd_seconds_per_application",
        )

        resolved: list[TeamProviderRotationContribution] = []
        unresolved: list[str] = []
        for contribution in contributions:
            build = contribution.build
            plan = contribution.plan
            contributor = f"{plan.character_name} / {plan.build_name}"
            self._validate_identity(build, plan)

            timing = self.timing_service.resolve(build)
            slots = self.slot_service.resolve(build)
            timing_by_action = {
                (item.action_kind, item.action_name.casefold()): item.occupancy_seconds
                for item in timing.occupancy_requirements
            }
            unresolved_timing_names = {
                item.casefold() for item in timing.unresolved_action_names
            }
            slots_by_action = {
                (item.action_kind, item.action_name.casefold()): item.allowed_bars
                for item in slots.slot_requirements
            }
            plan_actions = {
                (float(item.time_seconds), item.sequence): item for item in plan.actions
            }

            action_costs: list[TeamProviderScheduledActionCost] = []
            seen: set[tuple[float, int]] = set()
            for reference in contribution.provider_actions:
                reference_key = (float(reference.time_seconds), reference.sequence)
                if reference_key in seen:
                    raise ValueError(
                        f"duplicate canonical provider action for {contributor} at {reference_key}"
                    )
                seen.add(reference_key)
                action = plan_actions.get(reference_key)
                if action is None or action.kind not in {
                    RotationActionKind.SKILL,
                    RotationActionKind.ULTIMATE,
                }:
                    action_costs.append(
                        TeamProviderScheduledActionCost(
                            time_seconds=reference.time_seconds,
                            sequence=reference.sequence,
                            gcd_seconds=gcd_seconds,
                            cast_channel_seconds=None,
                            resource_costs=None,
                            primary_role_displacement_seconds=(
                                reference.primary_role_displacement_seconds
                            ),
                        )
                    )
                    continue

                action_name = str(action.name or "").strip()
                action_key = (action.kind, action_name.casefold())
                allowed_bars = slots_by_action.get(action_key)
                if allowed_bars is None:
                    unresolved.append(
                        f"{contributor}: canonical saved-build slot ownership not found for "
                        f"{action.kind.value} {action_name!r}"
                    )
                elif action.bar not in allowed_bars:
                    unresolved.append(
                        f"{contributor}: {action_name!r} is scheduled on {action.bar or 'no'} bar "
                        f"but saved-build ownership is {', '.join(allowed_bars)}"
                    )

                if action_name.casefold() in unresolved_timing_names:
                    cast_channel_seconds = None
                    unresolved.extend(
                        f"{contributor}: {detail}"
                        for detail in timing.unresolved
                        if action_name.casefold() in detail.casefold()
                    )
                else:
                    cast_channel_seconds = timing_by_action.get(action_key, 0.0)

                resolution = self.ability_cost_repository.resolve_name(action_name)
                resource_costs: tuple[tuple[str, float], ...] | None = None
                ultimate_cost: float | None = None
                base_cost = resolution.base_cost
                if base_cost is None:
                    unresolved.extend(
                        f"{contributor}: {detail}" for detail in resolution.unresolved
                    )
                else:
                    final_resolution = self.final_cost_resolver.resolve(
                        build,
                        base_cost,
                        skill_line=resolution.skill_line,
                        progression=contribution.progression,
                    )
                    if final_resolution.unresolved or final_resolution.final_cost is None:
                        unresolved.extend(
                            f"{contributor}: {detail}"
                            for detail in final_resolution.unresolved
                        )
                    elif action.kind is RotationActionKind.ULTIMATE:
                        final_costs = final_resolution.final_cost.resource_costs
                        if (
                            len(final_costs) == 1
                            and final_costs[0].resource is ResourceType.ULTIMATE
                        ):
                            ultimate_cost = float(final_costs[0].final_amount)
                            resource_costs = ()
                        else:
                            unresolved.append(
                                f"{contributor}: saved Ultimate {action_name!r} did not resolve "
                                "to one canonical Ultimate resource cost"
                            )
                    else:
                        final_costs = final_resolution.final_cost.resource_costs
                        if any(
                            item.resource is ResourceType.ULTIMATE for item in final_costs
                        ):
                            unresolved.append(
                                f"{contributor}: provider skill {action_name!r} has an "
                                "Ultimate-linked resource cost"
                            )
                        else:
                            resource_costs = tuple(
                                (item.resource.value, float(item.final_amount))
                                for item in final_costs
                            )

                action_costs.append(
                    TeamProviderScheduledActionCost(
                        time_seconds=reference.time_seconds,
                        sequence=reference.sequence,
                        gcd_seconds=gcd_seconds,
                        cast_channel_seconds=cast_channel_seconds,
                        resource_costs=resource_costs,
                        ultimate_cost=ultimate_cost,
                        primary_role_displacement_seconds=(
                            reference.primary_role_displacement_seconds
                        ),
                    )
                )

            resolved.append(
                TeamProviderRotationContribution(
                    plan=plan,
                    provider_actions=tuple(action_costs),
                )
            )

        workload = self.workload_service.assess(
            alternative_id=alternative_id,
            effect_key=effect_key,
            duration_seconds=duration_seconds,
            recipient_coverage_met=recipient_coverage_met,
            temporal_coverage_met=temporal_coverage_met,
            contributions=tuple(resolved),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
        return TeamProviderCanonicalWorkloadProjection(
            workload=workload,
            resolved_contributions=tuple(resolved),
        )

    @staticmethod
    def _validate_identity(build: PlayerBuild, plan: RotationPlan) -> None:
        character_name = str(getattr(build, "Name", "") or "").strip()
        build_name = str(getattr(build, "BuildName", "") or "").strip()
        if not character_name or not build_name:
            raise ValueError("canonical provider contribution requires saved character/build identity")
        if character_name.casefold() != plan.character_name.casefold():
            raise ValueError("provider rotation plan character does not match saved build")
        if build_name.casefold() != plan.build_name.casefold():
            raise ValueError("provider rotation plan build does not match saved build")

    @staticmethod
    def _optional_positive(value: float | None, *, field_name: str) -> float | None:
        if value is None:
            return None
        normalized = float(value)
        if not isfinite(normalized) or normalized <= 0:
            raise ValueError(f"{field_name} must be finite and positive")
        return normalized


__all__ = [
    "TeamProviderCanonicalActionReference",
    "TeamProviderCanonicalContribution",
    "TeamProviderCanonicalWorkloadProjection",
    "TeamProviderCanonicalWorkloadService",
]
