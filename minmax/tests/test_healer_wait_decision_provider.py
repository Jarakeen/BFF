from minmax.healer_wait_decision_provider import (
    HealerHeavyAttackCandidate,
    HealerWaitDecisionProvider,
)
from minmax.heavy_attack_opportunity import (
    HeavyAttackOpportunityEvidence,
    HeavyAttackPurpose,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind
from minmax.rotation_recast import RotationRecastRule
from minmax.rotation_wait_decision import PrematureRecastDecisionContext


def _context(bar="front") -> PrematureRecastDecisionContext:
    candidate = RotationAction(10.0, 1, RotationActionKind.SKILL, "Combat Prayer", bar)
    return PrematureRecastDecisionContext(
        time_seconds=10.0,
        bar=bar,
        candidate=candidate,
        slot=candidate,
        next_due=(("combat prayer", bar, 15.0),),
        rules=(RotationRecastRule("Combat Prayer", 10.0, bar=bar),),
    )


def _required(*, allowed=True, higher=False):
    return HeavyAttackOpportunityEvidence(
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        purpose=HeavyAttackPurpose.REQUIRED_EFFECT,
        available_window_seconds=2.0,
        required_window_seconds=1.8,
        encounter_allows_channel=allowed,
        higher_priority_action_ready=higher,
        requirement_name="Roaring Opportunist",
    )


def _recovery(*, current=5000.0):
    return HeavyAttackOpportunityEvidence(
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        purpose=HeavyAttackPurpose.RECOVERY,
        available_window_seconds=2.0,
        required_window_seconds=1.8,
        needed_resource=ResourceType.MAGICKA,
        current_resource=current,
        maximum_resource=30000.0,
        recovery_trigger_fraction=0.30,
    )


def test_required_effect_heavy_wins_over_recovery_candidate() -> None:
    provider = HealerWaitDecisionProvider(
        candidates=(
            HealerHeavyAttackCandidate("front", _recovery()),
            HealerHeavyAttackCandidate("front", _required()),
        )
    )

    action = provider(_context())

    assert action is not None
    assert action.kind is RotationActionKind.HEAVY_ATTACK
    assert action.bar == "front"
    assert action.time_seconds == 10.0


def test_blocked_required_heavy_falls_through_to_safe_recovery_heavy() -> None:
    provider = HealerWaitDecisionProvider(
        candidates=(
            HealerHeavyAttackCandidate("front", _required(allowed=False)),
            HealerHeavyAttackCandidate("front", _recovery()),
        )
    )

    action = provider(_context())

    assert action is not None
    assert action.kind is RotationActionKind.HEAVY_ATTACK
    assert action.bar == "front"


def test_inactive_bar_heavy_candidate_is_ignored() -> None:
    provider = HealerWaitDecisionProvider(
        candidates=(HealerHeavyAttackCandidate("back", _required()),)
    )

    assert provider(_context("front")) is None


def test_no_recommended_heavy_preserves_wait_path() -> None:
    provider = HealerWaitDecisionProvider(
        candidates=(HealerHeavyAttackCandidate("front", _recovery(current=25000.0)),)
    )

    assert provider(_context()) is None
