from __future__ import annotations

from dataclasses import dataclass

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_resource_reserve import RotationResourceReserveRequirement
from models.build_model import PlayerBuild
from services.rotation_candidate_scorecard_service import RotationDemandActionRequirement
from services.rotation_sustain_service import RotationSustainService


@dataclass(frozen=True)
class RotationRequiredActionReserveDerivation:
    """Canonical minimum reserve implied by explicit required action costs.

    This is only a cast-affordability floor. It does not invent a healer safety
    buffer, emergency follow-up budget, or encounter-specific comfort margin.
    Those remain caller-owned policy layered on top of this derived minimum.
    """

    demand_name: str
    resource: ResourceType
    minimum_amount: int
    action_costs: tuple[tuple[str, int, int], ...]
    unresolved: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return not self.unresolved

    def as_requirement(self) -> RotationResourceReserveRequirement:
        if self.unresolved:
            raise ValueError(
                "cannot create resource reserve requirement from unresolved action costs: "
                + "; ".join(self.unresolved)
            )
        return RotationResourceReserveRequirement(
            demand_name=self.demand_name,
            resource=self.resource,
            minimum_amount=self.minimum_amount,
        )


class RotationRequiredActionReserveService:
    """Derive an evidence floor from explicit mechanic action obligations.

    The service reuses ``RotationSustainService`` for canonical build-specific
    action costs rather than maintaining a second cost formula. Required actions
    are placed at 0s on a minimal positive-duration synthetic plan so cost
    modifiers are resolved through the same Phase 4 path used by real rotation
    sustain while still satisfying the calculation-context duration contract.

    The resulting amount answers only: "what resource is minimally required to
    pay for these explicitly required casts?" It does not claim that amount is a
    sufficient gameplay safety reserve.
    """

    _SYNTHETIC_DURATION_SECONDS = 1.0

    def __init__(self, sustain_service: RotationSustainService | None = None) -> None:
        self.sustain_service = sustain_service or RotationSustainService()

    def derive(
        self,
        *,
        build: PlayerBuild,
        demand_name: str,
        requirements: tuple[RotationDemandActionRequirement, ...],
        resource: ResourceType = ResourceType.MAGICKA,
    ) -> RotationRequiredActionReserveDerivation:
        demand = str(demand_name or "").strip()
        if not demand:
            raise ValueError("required-action reserve demand name is required")

        matching = tuple(item for item in requirements if item.demand_name == demand)
        if not matching:
            raise ValueError(
                f"no explicit action requirements supplied for demand {demand!r}"
            )

        character_name = str(
            getattr(build, "CharacterName", "")
            or build.Name
            or build.Gamertag
            or ""
        ).strip()
        build_name = str(build.BuildName or "Current Build").strip()
        if not character_name:
            raise ValueError("saved build has no character identity for reserve derivation")

        actions: list[RotationAction] = []
        expected_counts: dict[str, int] = {}
        sequence = 0
        for requirement in matching:
            expected_counts[requirement.skill_name.casefold()] = (
                expected_counts.get(requirement.skill_name.casefold(), 0)
                + requirement.minimum_casts
            )
            for _ in range(requirement.minimum_casts):
                actions.append(
                    RotationAction(
                        time_seconds=0.0,
                        sequence=sequence,
                        kind=RotationActionKind.SKILL,
                        name=requirement.skill_name,
                        bar=requirement.bar,
                    )
                )
                sequence += 1

        plan = RotationPlan(
            character_name=character_name,
            build_name=build_name,
            duration_seconds=self._SYNTHETIC_DURATION_SECONDS,
            actions=tuple(actions),
        )
        projection = self.sustain_service.evaluate(
            build=build,
            plan=plan,
            resource=resource,
        )

        totals: dict[str, int] = {}
        counts: dict[str, int] = {}
        display_names: dict[str, str] = {}
        for event in projection.run.action_cost_events:
            key = str(event.source).strip().casefold()
            if not key:
                continue
            totals[key] = totals.get(key, 0) + int(event.amount)
            counts[key] = counts.get(key, 0) + 1
            display_names.setdefault(key, str(event.source).strip())

        unresolved = list(projection.unresolved)
        required_names = {item.skill_name.casefold(): item.skill_name for item in matching}
        for key, required_count in expected_counts.items():
            observed = counts.get(key, 0)
            if observed != required_count:
                unresolved.append(
                    f"{required_names[key]}: expected {required_count} canonical {resource.value} "
                    f"cost event(s), resolved {observed}"
                )

        action_costs = tuple(
            (
                display_names.get(key, required_names.get(key, key)),
                counts.get(key, 0),
                totals.get(key, 0),
            )
            for key in sorted(required_names)
        )
        minimum_amount = sum(amount for _, _, amount in action_costs)

        return RotationRequiredActionReserveDerivation(
            demand_name=demand,
            resource=resource,
            minimum_amount=minimum_amount,
            action_costs=action_costs,
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)
