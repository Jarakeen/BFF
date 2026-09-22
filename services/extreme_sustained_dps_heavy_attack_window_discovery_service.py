from __future__ import annotations

"""Discover and materialize the complete scheduler-legal Heavy Attack slot family."""

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_wait_decision import (
    PrematureRecastDecision,
    PrematureRecastDecisionContext,
)
from minmax.soft_action_duration_scheduler import (
    PriorityAwareSoftActionDurationRotationScheduler,
    SoftActionDurationRotationScheduler,
)
from services.extreme_sustained_dps_heavy_attack_policy_frontier_service import (
    ExtremeSustainedDPSHeavyAttackWindow,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)


_FULL_CHARGE_SECONDS = 1.8
_EPSILON = 1e-9


@dataclass(frozen=True)
class ExtremeSustainedDPSHeavyAttackChannelBlock:
    start_seconds: float
    end_seconds: float
    source: str

    def __post_init__(self) -> None:
        start = float(self.start_seconds)
        end = float(self.end_seconds)
        source = str(self.source or "").strip()
        if not math.isfinite(start) or start < 0.0:
            raise ValueError("Heavy Attack channel-block start must be finite and non-negative")
        if not math.isfinite(end) or end <= start:
            raise ValueError("Heavy Attack channel-block end must be finite and after start")
        if not source:
            raise ValueError("Heavy Attack channel block requires source evidence")
        object.__setattr__(self, "start_seconds", start)
        object.__setattr__(self, "end_seconds", end)
        object.__setattr__(self, "source", source)


@dataclass(frozen=True)
class ExtremeSustainedDPSHeavyAttackWindowDiscovery:
    windows: tuple[ExtremeSustainedDPSHeavyAttackWindow, ...]
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSHeavyAttackWindowDiscoveryService:
    """Probe every scheduled skill slot through the canonical channel scheduler."""

    @staticmethod
    def _slot_key(action: RotationAction) -> tuple[float, int, str]:
        return (
            float(action.time_seconds),
            int(action.sequence),
            str(action.bar or "").strip().casefold(),
        )

    @staticmethod
    def _blocked(
        *,
        start_seconds: float,
        end_seconds: float,
        blocks: tuple[ExtremeSustainedDPSHeavyAttackChannelBlock, ...],
    ) -> bool:
        for block in blocks:
            if (
                float(start_seconds) < float(block.end_seconds) - _EPSILON
                and float(end_seconds) > float(block.start_seconds) + _EPSILON
            ):
                return True
        return False

    @staticmethod
    def _scheduler(priorities):
        if priorities is None:
            return SoftActionDurationRotationScheduler()
        return PriorityAwareSoftActionDurationRotationScheduler(priorities)

    @classmethod
    def _provider(
        cls,
        selected_keys: set[tuple[float, int, str]],
        blocks: tuple[ExtremeSustainedDPSHeavyAttackChannelBlock, ...],
    ):
        def decide(
            context: PrematureRecastDecisionContext,
        ) -> PrematureRecastDecision | None:
            bar = str(context.slot.bar or "").strip().casefold()
            key = (
                float(context.slot.time_seconds),
                int(context.slot.sequence),
                bar,
            )
            if key not in selected_keys:
                return None

            end = float(context.slot.time_seconds) + _FULL_CHARGE_SECONDS
            if cls._blocked(
                start_seconds=context.slot.time_seconds,
                end_seconds=end,
                blocks=blocks,
            ):
                return None

            return PrematureRecastDecision(
                action=RotationAction(
                    time_seconds=context.slot.time_seconds,
                    sequence=context.slot.sequence,
                    kind=RotationActionKind.HEAVY_ATTACK,
                    name="Heavy Attack",
                    bar=context.slot.bar,
                ),
                reservation_seconds=_FULL_CHARGE_SECONDS,
            )

        return decide

    @classmethod
    def materialize(
        cls,
        *,
        seed: GeneratedRotationCandidate,
        windows: tuple[ExtremeSustainedDPSHeavyAttackWindow, ...],
        duration_rules: tuple[object, ...],
        priorities=None,
        channel_blocks: tuple[ExtremeSustainedDPSHeavyAttackChannelBlock, ...] = (),
    ) -> GeneratedRotationCandidate:
        selected = tuple(windows)
        selected_keys = {
            (float(row.time_seconds), int(row.sequence), row.bar)
            for row in selected
        }
        scheduler = cls._scheduler(priorities)
        plan = scheduler.refine(
            seed.plan,
            tuple(duration_rules),
            soft_decision=cls._provider(
                selected_keys,
                tuple(channel_blocks),
            ),
        )

        completion = (
            RotationHeavySustainProjectionService
            .completion_evidence_from_verified_reservations(plan)
        )
        completed_keys = {
            (
                float(item.action_time_seconds),
                int(item.action_sequence),
            )
            for item in completion
        }
        expected_keys = {
            (float(row.time_seconds), int(row.sequence))
            for row in selected
        }
        if completed_keys != expected_keys:
            raise ValueError(
                "canonical Heavy Attack scheduler did not preserve the selected "
                "fully charged reservation family"
            )

        return GeneratedRotationCandidate(
            candidate_id=(
                seed.candidate_id
                + "|heavy:"
                + (
                    "none"
                    if not selected
                    else ",".join(
                        f"{row.time_seconds:g}/{row.sequence}"
                        for row in selected
                    )
                )
            ),
            plan=plan,
            refresh_leads=seed.refresh_leads,
            action_claims=seed.action_claims,
        )

    @classmethod
    def discover(
        cls,
        *,
        seed: GeneratedRotationCandidate,
        duration_rules: tuple[object, ...],
        priorities=None,
        channel_blocks: tuple[ExtremeSustainedDPSHeavyAttackChannelBlock, ...] = (),
        channel_block_denominator_proven: bool = False,
    ) -> ExtremeSustainedDPSHeavyAttackWindowDiscovery:
        blocks = tuple(channel_blocks)
        unresolved: list[str] = []
        if not channel_block_denominator_proven:
            unresolved.append(
                "Heavy Attack encounter channel-block denominator is not proven complete"
            )

        skill_slots = tuple(
            action
            for action in seed.plan.actions
            if action.kind is RotationActionKind.SKILL
            and action.bar in {"front", "back"}
        )
        windows: list[ExtremeSustainedDPSHeavyAttackWindow] = []

        for slot in skill_slots:
            start = float(slot.time_seconds)
            end = start + _FULL_CHARGE_SECONDS
            if end > float(seed.plan.duration_seconds) + _EPSILON:
                continue
            if cls._blocked(
                start_seconds=start,
                end_seconds=end,
                blocks=blocks,
            ):
                continue

            window = ExtremeSustainedDPSHeavyAttackWindow(
                time_seconds=start,
                sequence=int(slot.sequence),
                bar=str(slot.bar),
                channel_seconds=_FULL_CHARGE_SECONDS,
                encounter_allows_channel=True,
            )
            try:
                candidate = cls.materialize(
                    seed=seed,
                    windows=(window,),
                    duration_rules=tuple(duration_rules),
                    priorities=priorities,
                    channel_blocks=blocks,
                )
            except ValueError:
                continue

            completion = (
                RotationHeavySustainProjectionService
                .completion_evidence_from_verified_reservations(candidate.plan)
            )
            if len(completion) != 1:
                continue
            windows.append(window)

        ordered = tuple(
            sorted(
                windows,
                key=lambda row: (
                    row.time_seconds,
                    row.sequence,
                    row.bar,
                ),
            )
        )
        deduped = tuple(dict.fromkeys(unresolved))
        return ExtremeSustainedDPSHeavyAttackWindowDiscovery(
            windows=ordered,
            denominator_proven=bool(channel_block_denominator_proven and not deduped),
            evidence=(
                f"Scheduled ordinary skill slots probed: {len(skill_slots)}",
                f"Scheduler-legal fully charged Heavy Attack starts: {len(ordered)}",
                f"Caller-reviewed encounter channel blocks: {len(blocks)}",
                "Every scheduled skill slot is tested through the canonical soft-action duration scheduler",
                "First casts, due refreshes, hard boundaries, horizon limits, and same-bar displacement are therefore inherited from the canonical scheduler",
                "Encounter demand windows are not treated as channel prohibitions unless explicit channel-block evidence says so",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSHeavyAttackChannelBlock",
    "ExtremeSustainedDPSHeavyAttackWindowDiscovery",
    "ExtremeSustainedDPSHeavyAttackWindowDiscoveryService",
]
