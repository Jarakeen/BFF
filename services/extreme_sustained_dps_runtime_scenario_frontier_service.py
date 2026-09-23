from __future__ import annotations

"""Scenario-facing builder for the canonical Objective #32 runtime_state frontier."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_runtime_effect_universe_service import (
    ExtremeSustainedDPSRuntimeEffectUniverseService,
)
from services.extreme_sustained_dps_runtime_effect_relevance_service import (
    ExtremeSustainedDPSRuntimeEffectRelevanceService,
)
from services.extreme_sustained_dps_runtime_event_skeleton_service import (
    ExtremeSustainedDPSRuntimeEventSkeletonService,
)
from services.extreme_sustained_dps_runtime_attempt_evidence_frontier_service import (
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService,
)
from services.extreme_sustained_dps_runtime_external_history_assembly_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService,
)
from services.extreme_sustained_dps_runtime_external_history_frontier_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult,
    ExtremeSustainedDPSRuntimeExternalHistoryFrontierService,
)
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
)
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
)
from services.extreme_sustained_dps_weapon_enchantment_activation_resolution_service import (
    ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService,
)
from services.extreme_sustained_dps_weapon_enchantment_attempt_binding_service import (
    ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeScenarioFrontierResult:
    runtime: ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def frontier(self):
        return self.runtime.frontier


class ExtremeSustainedDPSRuntimeScenarioFrontierService:
    """Compose all finite runtime-state evidence layers for one finalized plan."""

    def __init__(
        self,
        *,
        external_history_frontier: (
            ExtremeSustainedDPSRuntimeExternalHistoryFrontierService | None
        ) = None,
        runtime_effect_universe: (
            ExtremeSustainedDPSRuntimeEffectUniverseService | object | None
        ) = None,
        runtime_effect_scaling: object | None = None,
        weapon_enchantment_activation_service: object | None = None,
        weapon_enchantment_cooldown_state_resolver: object | None = None,
        weapon_enchantment_activation_resolution_service: object | None = None,
        weapon_enchantment_attempt_binding_service: object | None = None,
    ) -> None:
        self.external_history_frontier = (
            external_history_frontier
            or ExtremeSustainedDPSRuntimeExternalHistoryFrontierService()
        )
        self.runtime_effect_universe = runtime_effect_universe
        self.runtime_effect_scaling = runtime_effect_scaling
        self.weapon_enchantment_activation_service = (
            weapon_enchantment_activation_service
        )
        self.weapon_enchantment_cooldown_state_resolver = (
            weapon_enchantment_cooldown_state_resolver
        )
        self.weapon_enchantment_activation_resolution_service = (
            weapon_enchantment_activation_resolution_service
            or ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService()
        )
        self.weapon_enchantment_attempt_binding_service = (
            weapon_enchantment_attempt_binding_service
            or ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService()
        )

    @staticmethod
    def _invoke_weapon_enchantment_cooldown_state_resolver(
        resolver: object,
        *,
        candidate,
        activation_event: RuntimeEvent,
        enchantment_effects: tuple[EffectVariant, ...],
    ):
        if callable(resolver):
            return resolver(
                candidate=candidate,
                activation_event=activation_event,
                enchantment_effects=enchantment_effects,
            )
        method = getattr(resolver, "resolve", None)
        if method is None:
            raise TypeError(
                "weapon-enchantment cooldown-state resolver must be callable or expose resolve()"
            )
        return method(
            candidate=candidate,
            activation_event=activation_event,
            enchantment_effects=enchantment_effects,
        )

    def _bind_weapon_enchantment_attempts(
        self,
        *,
        candidate,
        events: tuple[RuntimeEvent, ...],
        effects: tuple[EffectVariant, ...],
    ) -> tuple[
        tuple[RuntimeEvent, ...],
        tuple[RuntimeEffectEventAttempt, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        enchantment_effects = tuple(
            effect
            for effect in effects
            if str(effect.trigger or "").strip()
            == WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER
        )
        enchantment_events = tuple(
            event
            for event in events
            if event.trigger == WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER
        )
        generic_events = tuple(
            event
            for event in events
            if event.trigger != WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER
        )
        if not enchantment_events:
            return generic_events, (), (), ()

        if not enchantment_effects:
            return (
                generic_events,
                (),
                (),
                (
                    "weapon-enchantment activation events exist without canonical weapon-enchantment EffectVariants",
                ),
            )

        if self.weapon_enchantment_cooldown_state_resolver is None:
            return (
                generic_events,
                (),
                (),
                (
                    "weapon-enchantment activation opportunities require explicit per-opportunity cooldown-state evidence",
                ),
            )

        fixed_attempts: list[RuntimeEffectEventAttempt] = []
        evidence: list[str] = []
        unresolved: list[str] = []
        no_proc_count = 0

        for event in enchantment_events:
            state_result = self._invoke_weapon_enchantment_cooldown_state_resolver(
                self.weapon_enchantment_cooldown_state_resolver,
                candidate=candidate,
                activation_event=event,
                enchantment_effects=enchantment_effects,
            )
            state_unresolved = tuple(
                getattr(state_result, "unresolved", ()) or ()
            )
            state_evidence = tuple(
                getattr(state_result, "evidence", ()) or ()
            )
            if hasattr(state_result, "states"):
                cooldown_states = tuple(getattr(state_result, "states") or ())
            else:
                cooldown_states = tuple(state_result or ())
            evidence.extend(str(item) for item in state_evidence if str(item).strip())
            if state_unresolved:
                unresolved.extend(
                    f"{event.time_seconds:g}s #{event.sequence}: {item}"
                    for item in state_unresolved
                    if str(item).strip()
                )
                continue

            resolution = self.weapon_enchantment_activation_resolution_service.resolve(
                activation_event=event,
                enchantment_effects=enchantment_effects,
                cooldown_states=cooldown_states,
            )
            binding = self.weapon_enchantment_attempt_binding_service.bind(resolution)
            evidence.extend(
                str(item)
                for item in tuple(binding.evidence)
                if str(item).strip()
            )
            if binding.unresolved:
                unresolved.extend(
                    f"{event.time_seconds:g}s #{event.sequence}: {item}"
                    for item in tuple(binding.unresolved)
                    if str(item).strip()
                )
                continue
            if binding.attempt is None:
                no_proc_count += 1
                continue
            fixed_attempts.append(binding.attempt)

        evidence.extend(
            (
                f"Weapon-enchantment activation opportunities resolved: {len(enchantment_events)}",
                f"Weapon-enchantment source-bound runtime attempts: {len(fixed_attempts)}",
                f"Weapon-enchantment opportunities proven no-proc: {no_proc_count}",
            )
        )
        return (
            generic_events,
            tuple(fixed_attempts),
            tuple(dict.fromkeys(evidence)),
            tuple(dict.fromkeys(unresolved)),
        )

    def build_from_candidate(
        self,
        *,
        candidate,
        player_build: PlayerBuild,
        effects: tuple[EffectVariant, ...] | None = None,
        occurrence_provider: object | None = None,
        target_identity: str | None = None,
        supplemental_events: tuple[RuntimeEvent, ...] = (),
        supplemental_event_denominator_proven: bool = False,
        supplemental_histories: tuple[
            ExtremeSustainedDPSRuntimeExternalHistoryChoice,
            ...,
        ] = (),
        supplemental_denominator_proven: bool,
        source: str,
        initial_bar: str = "front",
        omitted_scope: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSRuntimeScenarioFrontierResult:
        universe_evidence: tuple[str, ...] = ()
        universe_unresolved: tuple[str, ...] = ()
        if effects is None:
            if self.runtime_effect_universe is None:
                raise ValueError(
                    "candidate-facing runtime scenario builder requires explicit effects or canonical runtime effect universe"
                )
            universe = self.runtime_effect_universe.resolve(player_build)
            discovered_effects = tuple(universe.effects)
            scaling_evidence: tuple[str, ...] = ()
            scaling_unresolved: tuple[str, ...] = ()
            if self.runtime_effect_scaling is not None:
                scaling = self.runtime_effect_scaling.resolve(
                    build=player_build,
                    plan=candidate.plan,
                    effects=discovered_effects,
                )
                discovered_effects = tuple(scaling.effects)
                scaling_evidence = tuple(scaling.evidence)
                scaling_unresolved = tuple(scaling.unresolved)

            relevance = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify(
                discovered_effects
            )
            effects = tuple(relevance.relevant)
            universe_evidence = (
                *tuple(universe.evidence),
                *scaling_evidence,
                *tuple(relevance.evidence),
            )
            universe_unresolved = tuple(
                dict.fromkeys(
                    (
                        *tuple(universe.unresolved),
                        *scaling_unresolved,
                        *tuple(relevance.unresolved),
                    )
                )
            )
            if universe_unresolved:
                # Preserve a normal fail-closed frontier shape rather than
                # continuing with a partial effect universe.
                result = self.build(
                    plan=candidate.plan,
                    player_build=player_build,
                    events=(),
                    effects=(),
                    event_denominator_proven=False,
                    supplemental_histories=tuple(supplemental_histories),
                    supplemental_denominator_proven=bool(
                        supplemental_denominator_proven
                    ),
                    source=source,
                    initial_bar=initial_bar,
                    omitted_scope=tuple(omitted_scope),
                )
                return ExtremeSustainedDPSRuntimeScenarioFrontierResult(
                    runtime=result.runtime,
                    evidence=(
                        *universe_evidence,
                        *tuple(result.evidence),
                    ),
                    unresolved=tuple(
                        dict.fromkeys(
                            (
                                *universe_unresolved,
                                *tuple(result.unresolved),
                            )
                        )
                    ),
                )

        skeleton = ExtremeSustainedDPSRuntimeEventSkeletonService.build(
            candidate=candidate,
            effects=tuple(effects),
            occurrence_provider=occurrence_provider,
            target_identity=target_identity,
            supplemental_events=tuple(supplemental_events),
            supplemental_denominator_proven=bool(
                supplemental_event_denominator_proven
            ),
            weapon_enchantment_activation_service=(
                self.weapon_enchantment_activation_service
            ),
            source=f"{source}: runtime event skeletons",
        )
        (
            runtime_events,
            fixed_attempts,
            enchantment_binding_evidence,
            enchantment_binding_unresolved,
        ) = self._bind_weapon_enchantment_attempts(
            candidate=candidate,
            events=tuple(skeleton.events),
            effects=tuple(effects),
        )
        result = self.build(
            plan=candidate.plan,
            player_build=player_build,
            events=runtime_events,
            effects=tuple(effects),
            event_denominator_proven=bool(
                skeleton.denominator_proven
                and not enchantment_binding_unresolved
            ),
            fixed_attempts=fixed_attempts,
            supplemental_histories=tuple(supplemental_histories),
            supplemental_denominator_proven=bool(
                supplemental_denominator_proven
            ),
            source=source,
            initial_bar=initial_bar,
            omitted_scope=tuple(omitted_scope),
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *tuple(skeleton.unresolved),
                    *enchantment_binding_unresolved,
                    *tuple(result.unresolved),
                )
            )
        )
        return ExtremeSustainedDPSRuntimeScenarioFrontierResult(
            runtime=result.runtime,
            evidence=(
                *universe_evidence,
                *tuple(skeleton.evidence),
                *enchantment_binding_evidence,
                *tuple(result.evidence),
            ),
            unresolved=unresolved,
        )

    def build(
        self,
        *,
        plan,
        player_build: PlayerBuild,
        events: tuple[RuntimeEvent, ...],
        effects: tuple[EffectVariant, ...],
        event_denominator_proven: bool,
        fixed_attempts: tuple[RuntimeEffectEventAttempt, ...] = (),
        supplemental_histories: tuple[
            ExtremeSustainedDPSRuntimeExternalHistoryChoice,
            ...,
        ] = (),
        supplemental_denominator_proven: bool,
        source: str,
        initial_bar: str = "front",
        omitted_scope: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSRuntimeScenarioFrontierResult:
        attempts = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService.build(
            events=tuple(events),
            effects=tuple(effects),
            event_denominator_proven=bool(event_denominator_proven),
            source=f"{source}: runtime event skeletons",
            fixed_attempts=tuple(fixed_attempts),
        )
        assembled = ExtremeSustainedDPSRuntimeExternalHistoryAssemblyService.build(
            attempt_frontier=attempts,
            supplemental_histories=tuple(supplemental_histories),
            supplemental_denominator_proven=bool(
                supplemental_denominator_proven
            ),
            source=f"{source}: supplemental runtime history",
        )
        runtime = self.external_history_frontier.build(
            plan=plan,
            player_build=player_build,
            external_histories=tuple(assembled.choices),
            denominator_proven=bool(assembled.denominator_proven),
            source=source,
            initial_bar=initial_bar,
            omitted_scope=tuple(omitted_scope),
            effects=tuple(effects),
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *tuple(attempts.unresolved),
                    *tuple(assembled.unresolved),
                    *tuple(runtime.unresolved),
                )
            )
        )
        return ExtremeSustainedDPSRuntimeScenarioFrontierResult(
            runtime=runtime,
            evidence=(
                *tuple(attempts.evidence),
                *tuple(assembled.evidence),
                *tuple(runtime.evidence),
                (
                    "Objective #32 runtime_state scenario frontier is closure-ready"
                    if runtime.frontier.denominator_proven
                    and not runtime.frontier.omitted_scope
                    and not unresolved
                    else "Objective #32 runtime_state scenario frontier remains open"
                ),
            ),
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeScenarioFrontierResult",
    "ExtremeSustainedDPSRuntimeScenarioFrontierService",
]
