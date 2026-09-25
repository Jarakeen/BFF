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
    ExtremeSustainedDPSRuntimeAttemptEvidenceChoice,
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier,
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService,
)
from services.extreme_sustained_dps_runtime_attempt_frontier_composition_service import (
    ExtremeSustainedDPSRuntimeAttemptFrontierCompositionService,
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
from services.extreme_sustained_dps_weapon_enchantment_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService,
)
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonSequenceFrontierService,
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
        weapon_enchantment_cooldown_policy_resolver: object | None = None,
        weapon_enchantment_sequence_frontier_service: object | None = None,
        weapon_enchantment_activation_resolution_service: object | None = None,
        weapon_enchantment_attempt_binding_service: object | None = None,
        weapon_poison_activation_service: object | None = None,
        weapon_poison_sequence_frontier_service: object | None = None,
        weapon_poison_consequence_resolver: object | None = None,
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
        self.weapon_enchantment_cooldown_policy_resolver = (
            weapon_enchantment_cooldown_policy_resolver
        )
        self.weapon_enchantment_sequence_frontier_service = (
            weapon_enchantment_sequence_frontier_service
            or ExtremeSustainedDPSWeaponEnchantmentSequenceFrontierService()
        )
        self.weapon_enchantment_activation_resolution_service = (
            weapon_enchantment_activation_resolution_service
            or ExtremeSustainedDPSWeaponEnchantmentActivationResolutionService()
        )
        self.weapon_enchantment_attempt_binding_service = (
            weapon_enchantment_attempt_binding_service
            or ExtremeSustainedDPSWeaponEnchantmentAttemptBindingService()
        )
        self.weapon_poison_activation_service = weapon_poison_activation_service
        self.weapon_poison_sequence_frontier_service = (
            weapon_poison_sequence_frontier_service
            or ExtremeSustainedDPSWeaponPoisonSequenceFrontierService()
        )
        self.weapon_poison_consequence_resolver = weapon_poison_consequence_resolver

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

    @staticmethod
    def _invoke_weapon_poison_consequence_resolver(
        resolver: object,
        *,
        sequence_frontier,
        source: str,
    ):
        if callable(resolver):
            return resolver(
                sequence_frontier=sequence_frontier,
                source=source,
            )
        for method_name in ("build", "resolve"):
            method = getattr(resolver, method_name, None)
            if method is not None:
                return method(
                    sequence_frontier=sequence_frontier,
                    source=source,
                )
        raise TypeError(
            "weapon-poison consequence resolver must be callable or expose build()/resolve()"
        )

    @staticmethod
    def _invoke_weapon_enchantment_cooldown_policy_resolver(
        resolver: object,
        *,
        candidate,
        enchantment_effects: tuple[EffectVariant, ...],
        player_build: PlayerBuild,
    ):
        if callable(resolver):
            return resolver(
                candidate=candidate,
                enchantment_effects=enchantment_effects,
                player_build=player_build,
            )
        method = getattr(resolver, "resolve", None)
        if method is None:
            raise TypeError(
                "weapon-enchantment cooldown-policy resolver must be callable or expose resolve()"
            )
        return method(
            candidate=candidate,
            enchantment_effects=enchantment_effects,
            player_build=player_build,
        )

    def _weapon_enchantment_attempt_frontier(
        self,
        *,
        candidate,
        events: tuple[RuntimeEvent, ...],
        effects: tuple[EffectVariant, ...],
        event_denominator_proven: bool,
        source: str,
        player_build: PlayerBuild,
    ) -> tuple[
        tuple[RuntimeEvent, ...],
        ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier | None,
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
            return generic_events, None, (), ()

        if not enchantment_effects:
            return (
                generic_events,
                None,
                (),
                (
                    "weapon-enchantment activation events exist without canonical weapon-enchantment EffectVariants",
                ),
            )
        if self.weapon_enchantment_cooldown_policy_resolver is None:
            return generic_events, None, (), ()

        policy_result = self._invoke_weapon_enchantment_cooldown_policy_resolver(
            self.weapon_enchantment_cooldown_policy_resolver,
            candidate=candidate,
            enchantment_effects=enchantment_effects,
            player_build=player_build,
        )
        policy_unresolved = tuple(
            getattr(policy_result, "unresolved", ()) or ()
        )
        policy_evidence = tuple(
            str(item)
            for item in tuple(getattr(policy_result, "evidence", ()) or ())
            if str(item).strip()
        )
        if hasattr(policy_result, "policies"):
            policies = tuple(getattr(policy_result, "policies") or ())
        else:
            policies = tuple(policy_result or ())

        sequence = self.weapon_enchantment_sequence_frontier_service.build(
            events=enchantment_events,
            effects=enchantment_effects,
            policies=policies,
            event_denominator_proven=bool(
                event_denominator_proven and not policy_unresolved
            ),
            source=f"{source}: weapon-enchantment sequence",
        )
        choices = tuple(
            ExtremeSustainedDPSRuntimeAttemptEvidenceChoice(
                choice_id=choice.choice_id,
                attempts=tuple(choice.attempts),
                evidence=tuple(choice.evidence),
            )
            for choice in tuple(sequence.choices)
        )
        frontier = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier(
            choices=choices,
            candidate_count=len(choices),
            denominator_proven=bool(
                sequence.denominator_proven
                and not policy_unresolved
            ),
            evidence=(
                *policy_evidence,
                *tuple(sequence.evidence),
            ),
            unresolved=tuple(
                dict.fromkeys(
                    (
                        *policy_unresolved,
                        *tuple(sequence.unresolved),
                    )
                )
            ),
        )
        return (
            generic_events,
            frontier,
            tuple(frontier.evidence),
            tuple(frontier.unresolved),
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

    def _weapon_poison_runtime_frontier(
        self,
        *,
        candidate,
        player_build: PlayerBuild,
        occurrence_provider: object | None,
        target_identity: str | None,
        source: str,
    ) -> tuple[
        ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier | None,
        tuple[EffectVariant, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        front_poison = str(getattr(player_build, "FrontBarPoison", "") or "").strip()
        back_poison = str(getattr(player_build, "BackBarPoison", "") or "").strip()
        if not front_poison and not back_poison:
            return None, (), (), ()

        if self.weapon_poison_activation_service is None:
            return (
                None,
                (),
                (),
                (
                    "equipped weapon poison requires canonical poison activation-event authority",
                ),
            )
        if occurrence_provider is None:
            return (
                None,
                (),
                (),
                (
                    "equipped weapon poison requires canonical exact-time damage occurrence evidence",
                ),
            )

        activation = self.weapon_poison_activation_service.resolve(
            candidate=candidate,
            player_build=player_build,
            occurrence_provider=occurrence_provider,
            target_identity=target_identity,
        )
        evidence = list(tuple(getattr(activation, "evidence", ()) or ()))
        unresolved = list(tuple(getattr(activation, "unresolved", ()) or ()))
        frontier = self.weapon_poison_sequence_frontier_service.build(
            events=tuple(getattr(activation, "events", ()) or ()),
            player_build=player_build,
            event_denominator_proven=not unresolved,
            source=f"{source}: weapon-poison sequence",
        )
        evidence.extend(tuple(frontier.evidence))
        unresolved.extend(tuple(frontier.unresolved))

        possible_procs = any(
            tuple(getattr(choice, "procs", ()) or ())
            for choice in tuple(frontier.choices)
        )
        if not possible_procs:
            return (
                None,
                (),
                tuple(dict.fromkeys(row for row in evidence if str(row).strip())),
                tuple(dict.fromkeys(row for row in unresolved if str(row).strip())),
            )

        if self.weapon_poison_consequence_resolver is None:
            unresolved.append(
                "weapon-poison proc histories are finite, but selected poison effect "
                "identity/magnitude/dilution has no authoritative runtime consequence consumer"
            )
            return (
                None,
                (),
                tuple(dict.fromkeys(row for row in evidence if str(row).strip())),
                tuple(dict.fromkeys(row for row in unresolved if str(row).strip())),
            )

        try:
            consequence = self._invoke_weapon_poison_consequence_resolver(
                self.weapon_poison_consequence_resolver,
                sequence_frontier=frontier,
                source=f"{source}: weapon-poison consequences",
            )
        except (TypeError, ValueError) as exc:
            unresolved.append(
                "weapon-poison consequence resolution failed closed: "
                + str(exc)
            )
            return (
                None,
                (),
                tuple(dict.fromkeys(row for row in evidence if str(row).strip())),
                tuple(dict.fromkeys(row for row in unresolved if str(row).strip())),
            )

        evidence.extend(tuple(getattr(consequence, "evidence", ()) or ()))
        unresolved.extend(tuple(getattr(consequence, "unresolved", ()) or ()))
        consequence_frontier = getattr(consequence, "attempt_frontier", None)
        consequence_effects = tuple(getattr(consequence, "effects", ()) or ())

        if consequence_frontier is None:
            unresolved.append(
                "weapon-poison consequence resolver returned no finite runtime attempt frontier"
            )
        elif not bool(getattr(consequence_frontier, "denominator_proven", False)):
            unresolved.append(
                "weapon-poison consequence runtime attempt denominator is not proven complete"
            )
        if not consequence_effects:
            unresolved.append(
                "weapon-poison consequence resolver returned no runtime effects"
            )

        return (
            consequence_frontier,
            consequence_effects,
            tuple(dict.fromkeys(row for row in evidence if str(row).strip())),
            tuple(dict.fromkeys(row for row in unresolved if str(row).strip())),
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
        weapon_enchantment_control_effects: tuple[EffectVariant, ...] = ()
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

            weapon_enchantment_control_effects = tuple(
                effect
                for effect in discovered_effects
                if str(effect.trigger or "").strip()
                == WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER
            )
            consequence_candidates = tuple(
                effect
                for effect in discovered_effects
                if effect not in weapon_enchantment_control_effects
            )
            relevance = ExtremeSustainedDPSRuntimeEffectRelevanceService.classify(
                consequence_candidates
            )
            effects = tuple(relevance.relevant)
            universe_evidence = (
                *tuple(universe.evidence),
                *scaling_evidence,
                f"Weapon-enchantment runtime control variants separated from combat consequences: {len(weapon_enchantment_control_effects)}",
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

        else:
            weapon_enchantment_control_effects = tuple(
                effect
                for effect in tuple(effects)
                if str(effect.trigger or "").strip()
                == WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER
            )
            effects = tuple(
                effect
                for effect in tuple(effects)
                if effect not in weapon_enchantment_control_effects
            )

        base_consequence_effects = tuple(effects)
        event_effects = (
            *base_consequence_effects,
            *weapon_enchantment_control_effects,
        )

        (
            poison_attempt_frontier,
            poison_effects,
            poison_evidence,
            poison_unresolved,
        ) = self._weapon_poison_runtime_frontier(
            candidate=candidate,
            player_build=player_build,
            occurrence_provider=occurrence_provider,
            target_identity=target_identity,
            source=source,
        )
        consequence_effects = (
            *base_consequence_effects,
            *tuple(poison_effects),
        )

        skeleton = ExtremeSustainedDPSRuntimeEventSkeletonService.build(
            candidate=candidate,
            effects=tuple(event_effects),
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
            enchantment_attempt_frontier,
            enchantment_binding_evidence,
            enchantment_binding_unresolved,
        ) = self._weapon_enchantment_attempt_frontier(
            candidate=candidate,
            events=tuple(skeleton.events),
            effects=tuple(event_effects),
            event_denominator_proven=bool(skeleton.denominator_proven),
            source=source,
            player_build=player_build,
        )
        fixed_attempts: tuple[RuntimeEffectEventAttempt, ...] = ()
        if (
            enchantment_attempt_frontier is None
            and any(
                event.trigger == WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER
                for event in tuple(skeleton.events)
            )
        ):
            (
                runtime_events,
                fixed_attempts,
                enchantment_binding_evidence,
                enchantment_binding_unresolved,
            ) = self._bind_weapon_enchantment_attempts(
                candidate=candidate,
                events=tuple(skeleton.events),
                effects=tuple(event_effects),
            )

        fixed_frontiers = tuple(
            frontier
            for frontier in (
                enchantment_attempt_frontier,
                poison_attempt_frontier,
            )
            if frontier is not None
        )
        fixed_attempt_frontier = None
        if len(fixed_frontiers) == 1:
            fixed_attempt_frontier = fixed_frontiers[0]
        elif len(fixed_frontiers) > 1:
            fixed_attempt_frontier = (
                ExtremeSustainedDPSRuntimeAttemptFrontierCompositionService.compose(
                    fixed_frontiers,
                    source=f"{source}: fixed runtime attempt composition",
                )
            )

        result = self.build(
            plan=candidate.plan,
            player_build=player_build,
            events=runtime_events,
            effects=tuple(consequence_effects),
            event_denominator_proven=bool(
                skeleton.denominator_proven
                and not poison_unresolved
                and not enchantment_binding_unresolved
            ),
            fixed_attempts=fixed_attempts,
            fixed_attempt_frontier=fixed_attempt_frontier,
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
                    *poison_unresolved,
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
                *poison_evidence,
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
        fixed_attempt_frontier: ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier | None = None,
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
        if fixed_attempt_frontier is not None:
            attempts = ExtremeSustainedDPSRuntimeAttemptFrontierCompositionService.compose(
                (
                    fixed_attempt_frontier,
                    attempts,
                ),
                source=f"{source}: runtime attempt composition",
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
