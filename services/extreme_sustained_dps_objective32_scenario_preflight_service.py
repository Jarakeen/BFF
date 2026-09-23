from __future__ import annotations

"""Preflight proof-critical search-time evidence for Objective #32 closure."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeSustainedDPSObjective32ScenarioPreflight:
    ready: bool
    evidence: tuple[str, ...]
    blockers: tuple[str, ...]


class ExtremeSustainedDPSObjective32ScenarioPreflightService:
    """Validate the search-time evidence composition cannot own statically."""

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

        candidate_runtime_present = bool(
            candidate_runtime_state_resolver is not None
            or candidate_runtime_state_resolver_present
        )
        if runtime_state_frontier is None and not candidate_runtime_present:
            blockers.append(
                "Objective #32 theoretical closure requires an explicit runtime-state frontier or candidate-resolved runtime-state authority"
            )
        elif runtime_state_frontier is not None:
            if not bool(
                getattr(runtime_state_frontier, "denominator_proven", False)
            ):
                blockers.append(
                    "Objective #32 runtime-state denominator is not proven complete"
                )
            unresolved = tuple(
                str(item).strip()
                for item in tuple(
                    getattr(runtime_state_frontier, "unresolved", ()) or ()
                )
                if str(item).strip()
            )
            blockers.extend(
                f"Objective #32 runtime-state evidence unresolved: {item}"
                for item in unresolved
            )
            omitted = tuple(
                str(item).strip()
                for item in tuple(
                    getattr(runtime_state_frontier, "omitted_scope", ()) or ()
                )
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
            if not bool(
                getattr(
                    candidate_runtime_state_resolver,
                    "supplemental_event_denominator_proven",
                    False,
                )
            ):
                blockers.append(
                    "Objective #32 candidate runtime-event denominator is not proven complete"
                )
            if not bool(
                getattr(
                    candidate_runtime_state_resolver,
                    "supplemental_history_denominator_proven",
                    False,
                )
            ):
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

        if not bool(heavy_attack_channel_block_denominator_proven):
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
                    if heavy_attack_channel_block_denominator_proven
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
