from __future__ import annotations

from dataclasses import dataclass
import math

from .named_combat_buffs import canonical_buff_name
from .support_target_type import SupportTargetType


@dataclass(frozen=True)
class ExternalGroupBuffApplication:
    """Explicit proof that one named support buff was applied by one actor to another.

    This contract is deliberately role-neutral. It records source identity,
    recipient identity, source target semantics, and the exact active window.
    Consumers may project only applications whose recipient legality and snapshot
    timing are proven. Merely knowing that a group member could provide a buff is
    not evidence that the evaluated character actually had it.
    """

    source_actor_id: str
    recipient_actor_id: str
    buff_name: str
    target_type: SupportTargetType
    applied_at_seconds: float
    duration_seconds: float
    source_evidence: str

    def __post_init__(self) -> None:
        source = str(self.source_actor_id or "").strip()
        recipient = str(self.recipient_actor_id or "").strip()
        evidence = str(self.source_evidence or "").strip()
        canonical = canonical_buff_name(self.buff_name)
        if not source:
            raise ValueError("external group buff source actor is required")
        if not recipient:
            raise ValueError("external group buff recipient actor is required")
        if canonical is None:
            raise ValueError(f"external group buff name is not canonical: {self.buff_name}")
        if not evidence:
            raise ValueError("external group buff source evidence is required")
        applied = float(self.applied_at_seconds)
        duration = float(self.duration_seconds)
        if not math.isfinite(applied) or applied < 0.0:
            raise ValueError("external group buff application time must be finite and non-negative")
        if not math.isfinite(duration) or duration <= 0.0:
            raise ValueError("external group buff duration must be finite and positive")
        object.__setattr__(self, "source_actor_id", source)
        object.__setattr__(self, "recipient_actor_id", recipient)
        object.__setattr__(self, "buff_name", canonical)
        object.__setattr__(self, "source_evidence", evidence)
        object.__setattr__(self, "applied_at_seconds", applied)
        object.__setattr__(self, "duration_seconds", duration)

    @property
    def ends_at_seconds(self) -> float:
        return self.applied_at_seconds + self.duration_seconds

    def is_active_at(self, snapshot_time_seconds: float) -> bool:
        snapshot = float(snapshot_time_seconds)
        if not math.isfinite(snapshot) or snapshot < 0.0:
            raise ValueError("external group buff snapshot time must be finite and non-negative")
        return self.applied_at_seconds <= snapshot < self.ends_at_seconds


@dataclass(frozen=True)
class ExternalGroupBuffProjection:
    active_buffs: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExternalGroupBuffProvenanceResolver:
    """Project explicitly evidenced external group buffs for one recipient snapshot."""

    @staticmethod
    def _recipient_legal(
        application: ExternalGroupBuffApplication,
        *,
        group_member_ids: frozenset[str],
    ) -> bool:
        source = application.source_actor_id
        recipient = application.recipient_actor_id
        target_type = application.target_type
        if target_type is SupportTargetType.SELF:
            return source == recipient
        if target_type is SupportTargetType.ALLY:
            return source != recipient and recipient in group_member_ids
        if target_type is SupportTargetType.SELF_OR_ALLY:
            return source == recipient or recipient in group_member_ids
        if target_type is SupportTargetType.GROUP:
            return recipient in group_member_ids
        return False

    def resolve(
        self,
        *,
        recipient_actor_id: str,
        group_member_ids: tuple[str, ...],
        snapshot_time_seconds: float,
        applications: tuple[ExternalGroupBuffApplication, ...],
    ) -> ExternalGroupBuffProjection:
        recipient = str(recipient_actor_id or "").strip()
        if not recipient:
            raise ValueError("external group buff projection recipient is required")
        members = frozenset(str(value or "").strip() for value in group_member_ids if str(value or "").strip())
        active: list[str] = []
        unresolved: list[str] = []

        for application in applications:
            if application.recipient_actor_id != recipient:
                continue
            if not self._recipient_legal(application, group_member_ids=members):
                unresolved.append(
                    f"External buff recipient is not legal for {application.buff_name}: "
                    f"source={application.source_actor_id}, recipient={application.recipient_actor_id}, "
                    f"target_type={application.target_type.value}"
                )
                continue
            if application.target_type is SupportTargetType.ENEMY:
                unresolved.append(
                    f"Enemy-targeted support effect cannot be projected as a friendly buff: {application.buff_name}"
                )
                continue
            if application.is_active_at(snapshot_time_seconds):
                active.append(application.buff_name)

        return ExternalGroupBuffProjection(
            active_buffs=tuple(dict.fromkeys(active)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
