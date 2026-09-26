from __future__ import annotations

"""Preflight proof-critical search-time evidence for Objective #32 closure."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeSustainedDPSObjective32ScenarioPreflight:
    ready: bool
    evidence: tuple[str, ...]
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.ready, bool):
            raise TypeError("Objective #32 scenario preflight ready must be boolean")
        if not isinstance(self.evidence, tuple):
            raise TypeError("Objective #32 scenario preflight evidence must be a tuple")
        if not isinstance(self.blockers, tuple):
            raise TypeError("Objective #32 scenario preflight blockers must be a tuple")


class ExtremeSustainedDPSObjective32ScenarioPreflightService:
    """Validate the search-time evidence composition cannot own statically."""

    @staticmethod
    def _strict_bool(value: object, label: str) -> bool:
        if not isinstance(value, bool):
            raise TypeError(f"{label} must be boolean")
        return value

    @classmethod
    def assess(
        cls,
        *,
        runtime_state_frontier: object | None,
        candidate_runtime_state_resolver: object | None = None,
        candidate_runtime_state_resolver_present: bool = False,
        heavy_attack_channel_block_denominator_proven: bool,
        encounter_policy_adapter: object | None,
    ) -> ExtremeSustainedDPSObjective32ScenarioPreflight:
        blockers: list[str] = []

        candidate_present_flag = cls._strict_bool(
            candidate_runtime_state_resolver_present,
            "candidate_runtime_state_resolver_present",
        )
        heavy_denominator_proven = cls._strict_bool(
            heavy_attack_channel_block_denominator_proven,
            "heavy_attack_channel_block_denominator_proven",
        )
        candidate_runtime_present = (
            candidate_runtime_state_resolver is not None
            or candidate_present_flag
        )
        if runtime_state_frontier is None and not candidate_runtime_present:
            blockers.append(
                "Objective #32 theoretical closure requires an explicit runtime-state frontier or candidate-resolved runtime-state authority"
            )
        elif runtime_state_frontier is not None:
            runtime_denominator = getattr(
                runtime_state_frontier,
                "denominator_proven",
                None,
            )
            if not isinstance(runtime_denominator, bool):
                raise TypeError(
                    "runtime_state_frontier.denominator_proven must be boolean"
                )
            if runtime_denominator is not True:
                blockers.append(
                    "Objective #32 runtime-state denominator is not proven complete"
                )
            raw_unresolved = getattr(runtime_state_frontier, "unresolved", ())
            if not isinstance(raw_unresolved, tuple):
                raise TypeError("runtime_state_frontier.unresolved must be a tuple")
            unresolved = tuple(
                str(item).strip()
                for item in raw_unresolved
                if str(item).strip()
            )
            blockers.extend(
                f"Objective #32 runtime-state evidence unresolved: {item}"
                for item in unresolved
            )
            raw_omitted = getattr(runtime_state_frontier, "omitted_scope", ())
            if not isinstance(raw_omitted, tuple):
                raise TypeError("runtime_state_frontier.omitted_scope must be a tuple")
            omitted = tuple(
                str(item).strip()
                for item in raw_omitted
                if str(item).strip()
            )
            blockers.extend(
                f"Objective #32 runtime-state theoretical scope omitted: {item}"
                for item in omitted
            )
        elif candidate_runtime_state_resolver is None:
            blockers.append(
                "Objective #32 candidate-resolved runtime-state authority is present but its closure evidence is not inspectable"
            )
        else:
            event_denominator = getattr(
                candidate_runtime_state_resolver,
                "supplemental_event_denominator_proven",
                None,
            )
            if not isinstance(event_denominator, bool):
                raise TypeError(
                    "candidate runtime supplemental_event_denominator_proven must be boolean"
                )
            if event_denominator is not True:
                blockers.append(
                    "Objective #32 candidate runtime-event denominator is not proven complete"
                )

            history_denominator = getattr(
                candidate_runtime_state_resolver,
                "supplemental_history_denominator_proven",
                None,
            )
            if not isinstance(history_denominator, bool):
                raise TypeError(
                    "candidate runtime supplemental_history_denominator_proven must be boolean"
                )
            if history_denominator is not True:
                blockers.append(
                    "Objective #32 candidate runtime-history denominator is not proven complete"
                )
            scenario_frontier = getattr(
                candidate_runtime_state_resolver,
                "scenario_frontier",
                None,
            )
            if scenario_frontier is None:
                blockers.append(
                    "Objective #32 candidate runtime-state authority is missing canonical scenario frontier"
                )
            else:
                if getattr(scenario_frontier, "runtime_effect_universe", None) is None:
                    blockers.append(
                        "Objective #32 candidate runtime-state authority is missing canonical runtime EffectVariant discovery"
                    )
                if getattr(scenario_frontier, "runtime_effect_scaling", None) is None:
                    blockers.append(
                        "Objective #32 candidate runtime-state authority is missing canonical runtime effect scaling"
                    )
                if getattr(
                    scenario_frontier,
                    "weapon_poison_activation_service",
                    None,
                ) is None:
                    blockers.append(
                        "Objective #32 candidate runtime-state authority is missing canonical weapon-poison activation-event authority"
                    )
                if getattr(
                    scenario_frontier,
                    "weapon_poison_consequence_resolver",
                    None,
                ) is None:
                    blockers.append(
                        "Objective #32 candidate runtime-state authority is missing explicit weapon-poison consequence authority"
                    )

        if heavy_denominator_proven is not True:
            blockers.append(
                "Objective #32 Heavy Attack encounter channel-block denominator is not proven complete"
            )

        if encounter_policy_adapter is None:
            blockers.append(
                "Objective #32 canonical encounter-policy adapter is missing"
            )

        deduped = tuple(dict.fromkeys(blockers))
        return ExtremeSustainedDPSObjective32ScenarioPreflight(
            ready=not deduped,
            evidence=(
                (
                    "Runtime-state frontier is present"
                    if runtime_state_frontier is not None
                    else (
                        "Candidate-resolved runtime-state authority is present"
                        if candidate_runtime_present
                        else "Runtime-state frontier is absent"
                    )
                ),
                (
                    "Heavy Attack encounter channel-block denominator is proven complete"
                    if heavy_denominator_proven
                    else "Heavy Attack encounter channel-block denominator is open"
                ),
                (
                    "Encounter-policy adapter is present"
                    if encounter_policy_adapter is not None
                    else "Encounter-policy adapter is absent"
                ),
                f"Objective #32 scenario preflight blockers: {len(deduped)}",
                "Scenario preflight is diagnostic/guard evidence only; it does not prove branch-and-bound completion or exact simulation completeness",
            ),
            blockers=deduped,
        )

    @classmethod
    def require_ready(
        cls,
        *,
        runtime_state_frontier: object | None,
        candidate_runtime_state_resolver: object | None = None,
        candidate_runtime_state_resolver_present: bool = False,
        heavy_attack_channel_block_denominator_proven: bool,
        encounter_policy_adapter: object | None,
    ) -> ExtremeSustainedDPSObjective32ScenarioPreflight:
        result = cls.assess(
            runtime_state_frontier=runtime_state_frontier,
            candidate_runtime_state_resolver=candidate_runtime_state_resolver,
            candidate_runtime_state_resolver_present=(
                candidate_runtime_state_resolver_present
            ),
            heavy_attack_channel_block_denominator_proven=(
                heavy_attack_channel_block_denominator_proven
            ),
            encounter_policy_adapter=encounter_policy_adapter,
        )
        if result.blockers:
            raise ValueError(
                "Objective #32 scenario is not closure-ready: "
                + "; ".join(result.blockers)
            )
        return result


__all__ = [
    "ExtremeSustainedDPSObjective32ScenarioPreflight",
    "ExtremeSustainedDPSObjective32ScenarioPreflightService",
]
