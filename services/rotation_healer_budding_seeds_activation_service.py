from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerDelayedHealSeed,
    RotationHealerPeriodicHealSeed,
    RotationHealerResolvedHealEvent,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
)


@dataclass(frozen=True)
class RotationHealerBuddingSeedsActivationProjection:
    """Consequences of reviewed Budding Seeds second-activation behavior.

    When Budding Seeds is activated again before its natural delayed bloom, the
    second activation triggers that already-pending bloom immediately. This
    service therefore removes the generic delayed/periodic seeds that the second
    activation would otherwise look like it created and emits the first field's
    delayed bloom at the second activation timestamp.

    The exact periodic-field termination boundary at that instant remains
    unresolved, so periodic seeds belonging to the transformed field are withheld
    rather than scheduled past a boundary we have not independently verified.
    """

    special_events: tuple[RotationHealerResolvedHealEvent, ...]
    delayed_seeds: tuple[RotationHealerDelayedHealSeed, ...]
    periodic_seeds: tuple[RotationHealerPeriodicHealSeed, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerBuddingSeedsActivationService:
    SOURCE_NAME = "Budding Seeds"
    BLOOM_COEFFICIENT = 1
    PERIODIC_COEFFICIENT = 2

    def project(
        self,
        *,
        plan: RotationPlan,
        healing: RotationHealerActionHealingProjection,
        delayed_evidence: RotationHealerDelayedRuntimeEvidence,
    ) -> RotationHealerBuddingSeedsActivationProjection:
        if delayed_evidence.source_name.casefold() != self.SOURCE_NAME.casefold():
            raise ValueError("Budding Seeds activation service requires Budding Seeds delayed evidence")
        if delayed_evidence.coefficient_number != self.BLOOM_COEFFICIENT:
            raise ValueError("Budding Seeds activation service requires bloom coefficient 1 evidence")

        actions = tuple(
            action
            for action in plan.actions
            if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
            and (action.name or "").casefold() == self.SOURCE_NAME.casefold()
        )
        delayed_by_sequence = {
            seed.sequence: seed
            for seed in healing.delayed_seeds
            if seed.source_name.casefold() == self.SOURCE_NAME.casefold()
            and seed.coefficient_number == self.BLOOM_COEFFICIENT
        }
        periodic_by_sequence = {
            seed.sequence: seed
            for seed in healing.periodic_seeds
            if seed.source_name.casefold() == self.SOURCE_NAME.casefold()
            and seed.coefficient_number == self.PERIODIC_COEFFICIENT
        }

        consumed_sequences: set[int] = set()
        transformed_periodic_sequences: set[int] = set()
        special_events: list[RotationHealerResolvedHealEvent] = []
        unresolved: list[str] = []

        index = 0
        while index < len(actions) - 1:
            first = actions[index]
            second = actions[index + 1]
            first_seed = delayed_by_sequence.get(first.sequence)
            if first_seed is None:
                index += 1
                continue

            natural_bloom = first.time_seconds + delayed_evidence.delay_seconds
            if second.time_seconds < natural_bloom and not math.isclose(
                second.time_seconds,
                natural_bloom,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                special_events.append(
                    RotationHealerResolvedHealEvent(
                        time_seconds=second.time_seconds,
                        sequence=second.sequence,
                        source_name=self.SOURCE_NAME,
                        coefficient_number=self.BLOOM_COEFFICIENT,
                        modeled_heal=first_seed.modeled_heal,
                    )
                )
                consumed_sequences.update({first.sequence, second.sequence})
                if first.sequence in periodic_by_sequence:
                    transformed_periodic_sequences.add(first.sequence)
                if second.sequence in periodic_by_sequence:
                    transformed_periodic_sequences.add(second.sequence)
                unresolved.append(
                    "Budding Seeds coefficient 2: periodic field termination boundary at second activation is not independently verified"
                )
                index += 2
                continue

            index += 1

        delayed_seeds = tuple(
            seed
            for seed in healing.delayed_seeds
            if not (
                seed.source_name.casefold() == self.SOURCE_NAME.casefold()
                and seed.coefficient_number == self.BLOOM_COEFFICIENT
                and seed.sequence in consumed_sequences
            )
        )
        periodic_seeds = tuple(
            seed
            for seed in healing.periodic_seeds
            if not (
                seed.source_name.casefold() == self.SOURCE_NAME.casefold()
                and seed.coefficient_number == self.PERIODIC_COEFFICIENT
                and seed.sequence in transformed_periodic_sequences
            )
        )

        return RotationHealerBuddingSeedsActivationProjection(
            special_events=tuple(
                sorted(
                    special_events,
                    key=lambda item: (
                        item.time_seconds,
                        item.sequence,
                        item.source_name.casefold(),
                        item.coefficient_number,
                    ),
                )
            ),
            delayed_seeds=delayed_seeds,
            periodic_seeds=periodic_seeds,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
