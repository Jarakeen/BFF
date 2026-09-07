from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from .healer_heavy_attack_runtime_candidates import build_required_heavy_attack_candidates
from .healer_recovery_heavy_pressure import HealerRecoveryHeavyPressure
from .healer_recovery_heavy_runtime_candidates import build_recovery_heavy_attack_candidate
from .healer_wait_decision_provider import HealerWaitDecisionProvider
from .heavy_attack_runtime_state import HeavyAttackEffectRuntimeState
from .heavy_attack_wait_window import derive_heavy_attack_decision_window
from .rotation_wait_decision import (
    PrematureRecastDecision,
    PrematureRecastDecisionContext,
)


RecoveryHeavyPressureResolver = Callable[
    [PrematureRecastDecisionContext],
    HealerRecoveryHeavyPressure | None,
]


def unique_recovery_incentives(
    incentives: tuple[HealerHeavyAttackBuildIncentive, ...],
) -> tuple[HealerHeavyAttackBuildIncentive, ...]:
    """Collapse equivalent recovery opportunities to one candidate per bar/weapon.

    Build discovery may expose multiple pieces of evidence for the same fully charged
    heavy, for example base Restoration Staff Magicka recovery plus Cycle of Life.
    Those remain distinct static evidence, but they do not represent two different
    runtime actions. Caller order is preserved so the first discovered incentive is
    the representative scheduling opportunity.
    """

    seen: set[tuple[str, object]] = set()
    result: list[HealerHeavyAttackBuildIncentive] = []
    for incentive in incentives:
        if incentive.kind is not HeavyAttackBuildIncentiveKind.RECOVERY_VALUE:
            continue
        key = (incentive.bar, incentive.weapon)
        if key in seen:
            continue
        seen.add(key)
        result.append(incentive)
    return tuple(result)


@dataclass
class RuntimeHealerWaitDecisionProvider:
    """Convert required/recovery heavy evidence into safe WAIT replacements.

    Build discovery owns which heavy-attack incentives exist. Runtime state owns
    required-effect recurrence eligibility. An optional pressure resolver owns the
    current resource/reserve evidence for recovery heavies. The duration WAIT
    context owns refresh deadlines and hard timeline boundaries. Encounter safety
    and higher-priority readiness remain explicit caller evidence because this
    provider has no authority to invent mechanic or emergency-heal state.

    REQUIRED_EFFECT candidates retain priority over RECOVERY candidates through
    ``HealerWaitDecisionProvider``. Multiple static recovery facts for the same
    bar/weapon collapse to one runtime recovery opportunity. A scheduled fully
    charged heavy reserves ``required_window_seconds`` of the timeline so ordinary
    same-bar skill decisions inside the channel are displaced instead of overlapping
    the heavy. Required-effect triggers are recorded at channel completion so later
    WAIT points in the same generated plan respect effect recurrence.
    """

    incentives: tuple[HealerHeavyAttackBuildIncentive, ...]
    required_window_seconds: float
    runtime_states: tuple[HeavyAttackEffectRuntimeState, ...] = ()
    encounter_allows_channel: bool = True
    higher_priority_action_ready: bool = False
    recovery_pressure_resolver: RecoveryHeavyPressureResolver | None = None

    def __call__(
        self,
        context: PrematureRecastDecisionContext,
    ) -> PrematureRecastDecision | None:
        window = derive_heavy_attack_decision_window(
            context=context,
            required_window_seconds=self.required_window_seconds,
            encounter_allows_channel=self.encounter_allows_channel,
            higher_priority_action_ready=self.higher_priority_action_ready,
        )
        required_candidates = build_required_heavy_attack_candidates(
            incentives=self.incentives,
            window=window,
            runtime_states=self.runtime_states,
        )

        recovery_candidates = []
        if self.recovery_pressure_resolver is not None:
            pressure = self.recovery_pressure_resolver(context)
            if pressure is not None:
                for incentive in unique_recovery_incentives(self.incentives):
                    candidate = build_recovery_heavy_attack_candidate(
                        incentive=incentive,
                        pressure=pressure,
                        window=window,
                    )
                    if candidate is not None:
                        recovery_candidates.append(candidate)

        candidates = tuple(required_candidates) + tuple(recovery_candidates)
        if not candidates:
            return None

        action = HealerWaitDecisionProvider(candidates)(context)
        if action is None:
            return None

        completion_time = float(context.time_seconds) + float(self.required_window_seconds)
        self._record_triggers(required_candidates, completion_time)
        return PrematureRecastDecision(
            action=action,
            reservation_seconds=float(self.required_window_seconds),
        )

    def _record_triggers(self, candidates, completion_time: float) -> None:
        by_key = {
            (state.incentive_name.casefold(), state.bar): state
            for state in self.runtime_states
        }
        for candidate in candidates:
            name = str(candidate.evidence.requirement_name or "").strip()
            if not name:
                continue
            by_key[(name.casefold(), candidate.bar)] = HeavyAttackEffectRuntimeState(
                incentive_name=name,
                bar=candidate.bar,
                last_trigger_seconds=completion_time,
            )
        self.runtime_states = tuple(
            by_key[key]
            for key in sorted(by_key, key=lambda value: (value[1], value[0]))
        )
