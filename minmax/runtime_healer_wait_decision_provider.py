from __future__ import annotations

from dataclasses import dataclass

from .healer_heavy_attack_build_discovery import HealerHeavyAttackBuildIncentive
from .healer_heavy_attack_runtime_candidates import build_required_heavy_attack_candidates
from .healer_wait_decision_provider import HealerWaitDecisionProvider
from .heavy_attack_runtime_state import HeavyAttackEffectRuntimeState
from .heavy_attack_wait_window import derive_heavy_attack_decision_window
from .rotation_plan import RotationAction
from .rotation_wait_decision import PrematureRecastDecisionContext


@dataclass(frozen=True)
class RuntimeHealerWaitDecisionProvider:
    """Convert due required-heavy incentives into safe WAIT replacements.

    Build discovery owns which required heavy effects exist. Runtime state owns
    recurrence eligibility. The duration WAIT context owns the next scheduled
    decision and refresh deadlines. Encounter safety and higher-priority readiness
    remain explicit caller evidence because this provider has no authority to
    invent mechanic or emergency-heal state.
    """

    incentives: tuple[HealerHeavyAttackBuildIncentive, ...]
    required_window_seconds: float
    runtime_states: tuple[HeavyAttackEffectRuntimeState, ...] = ()
    encounter_allows_channel: bool = True
    higher_priority_action_ready: bool = False

    def __call__(self, context: PrematureRecastDecisionContext) -> RotationAction | None:
        window = derive_heavy_attack_decision_window(
            context=context,
            required_window_seconds=self.required_window_seconds,
            encounter_allows_channel=self.encounter_allows_channel,
            higher_priority_action_ready=self.higher_priority_action_ready,
        )
        candidates = build_required_heavy_attack_candidates(
            incentives=self.incentives,
            window=window,
            runtime_states=self.runtime_states,
        )
        if not candidates:
            return None
        return HealerWaitDecisionProvider(candidates)(context)
