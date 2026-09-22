from __future__ import annotations

"""Build Objective #32 runtime_state from a proven finite external-history family."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateFrontier,
    ExtremeSustainedDPSRuntimeStateFrontierService,
    ExtremeSustainedDPSRuntimeStateChoice,
)
from services.extreme_sustained_dps_runtime_witness_composition_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryChoice,
    ExtremeSustainedDPSRuntimeWitnessCompositionService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult:
    frontier: ExtremeSustainedDPSRuntimeStateFrontier
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSRuntimeExternalHistoryFrontierService:
    """Compose a proven external-history denominator into runtime-state witnesses."""

    def __init__(
        self,
        *,
        witness_composer: ExtremeSustainedDPSRuntimeWitnessCompositionService | None = None,
    ) -> None:
        self.witness_composer = (
            witness_composer
            or ExtremeSustainedDPSRuntimeWitnessCompositionService()
        )

    def build(
        self,
        *,
        plan,
        player_build: PlayerBuild,
        external_histories: tuple[
            ExtremeSustainedDPSRuntimeExternalHistoryChoice,
            ...,
        ],
        denominator_proven: bool,
        source: str,
        initial_bar: str = "front",
        omitted_scope: tuple[str, ...] = (),
        effects: tuple[EffectVariant, ...] = (),
    ) -> ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult:
        unresolved: list[str] = []
        runtime_choices: list[ExtremeSustainedDPSRuntimeStateChoice] = []
        seen: set[str] = set()

        for history in external_histories:
            if history.history_id in seen:
                unresolved.append(
                    f"Duplicate external runtime history identity: {history.history_id}"
                )
                continue
            seen.add(history.history_id)

            choice_unresolved = list(history.unresolved)
            witness = self.witness_composer.compose(
                plan=plan,
                player_build=player_build,
                external_entries=history.entries,
                initial_bar=initial_bar,
            )
            choice_unresolved.extend(tuple(witness.unresolved))
            if witness.snapshot is None:
                unresolved.extend(
                    f"{history.history_id}: {item}"
                    for item in choice_unresolved
                )
                continue

            runtime_choices.append(
                ExtremeSustainedDPSRuntimeStateChoice(
                    runtime_state_id=history.history_id,
                    snapshot=witness.snapshot,
                    evidence=(
                        *tuple(history.evidence),
                        *tuple(witness.evidence),
                    ),
                    effects=tuple(effects),
                    unresolved=tuple(
                        dict.fromkeys(
                            str(item).strip()
                            for item in choice_unresolved
                            if str(item).strip()
                        )
                    ),
                )
            )

        if not external_histories:
            unresolved.append(
                "Finite external runtime-history family is empty"
            )
        if not denominator_proven:
            unresolved.append(
                "External runtime-history denominator is not proven complete"
            )

        deduped = tuple(dict.fromkeys(unresolved))
        frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
            tuple(runtime_choices),
            denominator_proven=bool(
                denominator_proven
                and not deduped
                and len(runtime_choices) == len(external_histories)
            ),
            source=source,
            omitted_scope=tuple(omitted_scope),
        )
        combined_unresolved = tuple(
            dict.fromkeys(
                (
                    *deduped,
                    *tuple(frontier.unresolved),
                )
            )
        )

        return ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult(
            frontier=frontier,
            evidence=(
                f"External runtime histories supplied: {len(external_histories)}",
                f"Runtime witnesses composed: {len(runtime_choices)}",
                (
                    "External runtime-history denominator is proven complete"
                    if denominator_proven
                    else "External runtime-history denominator remains open"
                ),
                "Plan-owned bar transitions and finalized potion timing are excluded from caller-owned runtime-state mutation scope",
            ),
            unresolved=combined_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult",
    "ExtremeSustainedDPSRuntimeExternalHistoryFrontierService",
]
