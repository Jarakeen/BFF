from __future__ import annotations

"""Resolve reviewed candidate-specific runtime EffectVariant scaling."""

from dataclasses import dataclass, replace

from minmax.character_build.effect_instance import EffectVariant
from minmax.rotation_plan import RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_ultimate_service import RotationUltimateService


_MASTER_ARCHITECT_SCALING = "1 second per 10 Ultimate spent"
_ALKOSH_SCALING = "Weapon Damage, up to 6000 resistance reduction"


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeEffectScalingResult:
    effects: tuple[EffectVariant, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    source_data_unresolved: tuple[str, ...] = ()
    math_unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSRuntimeEffectScalingService:
    """Resolve only explicitly reviewed candidate-specific scaling semantics."""

    def __init__(
        self,
        *,
        ultimate_service: RotationUltimateService | object,
    ) -> None:
        self.ultimate_service = ultimate_service

    @classmethod
    def from_database(cls, database_path):
        return cls(ultimate_service=RotationUltimateService(database_path))

    def resolve(
        self,
        *,
        build: PlayerBuild,
        plan: RotationPlan,
        effects: tuple[EffectVariant, ...],
    ) -> ExtremeSustainedDPSRuntimeEffectScalingResult:
        resolved: list[EffectVariant] = []
        evidence: list[str] = []
        unresolved: list[str] = []
        source_data_unresolved: list[str] = []
        math_unresolved: list[str] = []

        for effect in effects:
            scaling = str(effect.scaling or "").strip()
            if not scaling:
                resolved.append(effect)
                continue

            if (
                effect.name == "major_slayer"
                and effect.trigger == "ultimate_activation_in_combat"
                and scaling == _MASTER_ARCHITECT_SCALING
            ):
                scaled, scaled_evidence, scaled_unresolved = (
                    self._resolve_master_architect(
                        build=build,
                        plan=plan,
                        effect=effect,
                    )
                )
                if scaled is not None:
                    resolved.append(scaled)
                evidence.extend(scaled_evidence)
                unresolved.extend(scaled_unresolved)
                source_data_unresolved.extend(scaled_unresolved)
                continue

            if (
                effect.name == "roar_of_alkosh"
                and effect.trigger == "synergy_activation"
                and scaling == _ALKOSH_SCALING
            ):
                message = (
                    f"{effect.source} {effect.name} requires activation-time Weapon Damage "
                    "to resolve resistance reduction up to 6000"
                )
                unresolved.append(message)
                source_data_unresolved.append(message)
                continue

            message = (
                f"{effect.source} {effect.name} runtime scaling is not reviewed: {scaling}"
            )
            unresolved.append(message)
            math_unresolved.append(message)

        return ExtremeSustainedDPSRuntimeEffectScalingResult(
            effects=tuple(resolved),
            evidence=tuple(dict.fromkeys(row for row in evidence if row)),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
            source_data_unresolved=tuple(
                dict.fromkeys(row for row in source_data_unresolved if row)
            ),
            math_unresolved=tuple(
                dict.fromkeys(row for row in math_unresolved if row)
            ),
        )

    def _resolve_master_architect(
        self,
        *,
        build: PlayerBuild,
        plan: RotationPlan,
        effect: EffectVariant,
    ) -> tuple[EffectVariant | None, tuple[str, ...], tuple[str, ...]]:
        ultimate_actions = tuple(
            action
            for action in plan.actions
            if action.kind is RotationActionKind.ULTIMATE
        )
        if not ultimate_actions:
            # No activation can occur, so candidate-specific duration scaling is
            # non-operative and must not block this branch.
            return (
                replace(effect, scaling=None),
                ("Master Architect has no scheduled Ultimate activation in this candidate",),
                (),
            )

        bars = tuple(
            dict.fromkeys(
                str(action.bar or "").strip().casefold()
                for action in ultimate_actions
                if str(action.bar or "").strip()
            )
        )
        if not bars:
            return (
                None,
                (),
                ("Master Architect duration requires bar-owned Ultimate spend evidence",),
            )

        costs: list[float] = []
        resolution_unresolved: list[str] = []
        for bar in bars:
            inputs = self.ultimate_service.resolve_generation_inputs(
                build=build,
                plan=plan,
                ultimate_bar=bar,
                generation_events=(),
                heroism_windows=(),
                use_scheduled_combat_attacks=False,
            )
            resolution_unresolved.extend(tuple(inputs.unresolved))
            if inputs.spend_rule is None:
                continue
            costs.append(float(inputs.spend_rule.cost))

        if resolution_unresolved or len(costs) != len(bars):
            return (
                None,
                (),
                tuple(
                    dict.fromkeys(
                        (
                            *resolution_unresolved,
                            "Master Architect duration could not resolve every scheduled Ultimate spend",
                        )
                    )
                ),
            )

        unique_costs = tuple(dict.fromkeys(round(cost, 9) for cost in costs))
        if len(unique_costs) != 1:
            return (
                None,
                (),
                (
                    "Master Architect candidate schedules Ultimates with different costs; "
                    "per-activation duration is not representable by one EffectVariant",
                ),
            )

        cost = float(unique_costs[0])
        if cost <= 0.0:
            return (
                None,
                (),
                ("Master Architect duration requires a positive canonical Ultimate spend",),
            )

        duration = cost / 10.0
        return (
            replace(
                effect,
                duration=float(duration),
                scaling=None,
            ),
            (
                f"Master Architect duration resolved from canonical Ultimate spend: "
                f"{cost:g} / 10 = {duration:g}s",
            ),
            (),
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeEffectScalingResult",
    "ExtremeSustainedDPSRuntimeEffectScalingService",
]
