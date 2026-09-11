from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.gameplay_policy_service import GameplayPolicy, GameplayPolicyService


class RotationGameplayPolicyStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    SATISFIED = "satisfied"
    DISFAVORED = "disfavored"
    OVERRIDDEN = "overridden"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class RotationGameplayPolicyContext:
    candidate_id: str
    role: str
    content_type: str
    personal_heal_skill_slots: tuple[str, ...] = ()
    reliable_group_healing: bool | None = None
    exception_contexts: tuple[str, ...] = ()
    personal_heal_slot_evidence_resolved: bool = True
    personal_heal_slot_unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("rotation gameplay policy context requires candidate_id")
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "role", _normalize_role(self.role))
        object.__setattr__(self, "content_type", str(self.content_type or "").strip().casefold())
        object.__setattr__(
            self,
            "personal_heal_skill_slots",
            _normalized_unique(self.personal_heal_skill_slots),
        )
        object.__setattr__(
            self,
            "exception_contexts",
            _normalized_unique(self.exception_contexts),
        )
        object.__setattr__(
            self,
            "personal_heal_slot_unresolved",
            _normalized_unique(self.personal_heal_slot_unresolved),
        )


@dataclass(frozen=True)
class RotationGameplayPolicyAssessment:
    candidate_id: str
    policy_id: str
    status: RotationGameplayPolicyStatus
    subject: str
    confidence: str
    reasons: tuple[str, ...]
    personal_heal_skill_slots: tuple[str, ...] = ()
    matched_exceptions: tuple[str, ...] = ()
    unknown_exception_contexts: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.status is not RotationGameplayPolicyStatus.UNRESOLVED

    @property
    def disfavored(self) -> bool:
        return self.status is RotationGameplayPolicyStatus.DISFAVORED


class RotationGameplayPolicyAssessmentService:
    """Apply explicit organized-endgame play-practice policy to rotation evidence.

    This service sits above canonical mechanics. It never decides that a skill is a
    personal heal from its name or tooltip; callers must supply already-resolved slot
    evidence. Encounter/assignment exceptions are likewise explicit evidence.
    """

    DD_PERSONAL_HEAL_POLICY_ID = "dd_redundant_personal_heal"
    ROLE_OVERRIDE_POLICY_ID = "encounter_assignment_overrides_role_default"

    def __init__(self, policy_service: GameplayPolicyService | None = None) -> None:
        self.policy_service = policy_service or GameplayPolicyService()

    def assess_dd_personal_heal(
        self,
        context: RotationGameplayPolicyContext,
    ) -> RotationGameplayPolicyAssessment:
        policy = self.policy_service.require(self.DD_PERSONAL_HEAL_POLICY_ID)
        self._validate_rotation_policy(policy)

        if not policy.applies_to(role=context.role, content_type=context.content_type):
            return self._assessment(
                context,
                policy,
                RotationGameplayPolicyStatus.NOT_APPLICABLE,
                ("policy does not apply to this role/content context",),
            )

        if not context.personal_heal_slot_evidence_resolved:
            reasons = ["personal-heal slot classification is unresolved"]
            reasons.extend(context.personal_heal_slot_unresolved)
            return self._assessment(
                context,
                policy,
                RotationGameplayPolicyStatus.UNRESOLVED,
                tuple(reasons),
            )

        if not context.personal_heal_skill_slots:
            return self._assessment(
                context,
                policy,
                RotationGameplayPolicyStatus.SATISFIED,
                ("no resolved personal-heal skill slot is present",),
            )

        known_exceptions = {value.casefold(): value for value in policy.exceptions}
        override_policy = self.policy_service.get(self.ROLE_OVERRIDE_POLICY_ID)
        override_contexts = {
            value.casefold(): value
            for value in (override_policy.override_contexts if override_policy is not None else ())
        }
        matched: list[str] = []
        unknown: list[str] = []
        for value in context.exception_contexts:
            key = value.casefold()
            if key in known_exceptions:
                matched.append(known_exceptions[key])
            elif key in override_contexts:
                matched.append(override_contexts[key])
            else:
                unknown.append(value)

        if context.reliable_group_healing is None:
            reasons = [
                "personal-heal slot is present but reliable group-healing coverage is unresolved",
            ]
            if unknown:
                reasons.append("unrecognized exception context does not establish an override")
            return self._assessment(
                context,
                policy,
                RotationGameplayPolicyStatus.UNRESOLVED,
                tuple(reasons),
                matched_exceptions=tuple(matched),
                unknown_exception_contexts=tuple(unknown),
            )

        if context.reliable_group_healing is False:
            return self._assessment(
                context,
                policy,
                RotationGameplayPolicyStatus.OVERRIDDEN,
                (
                    "personal-heal slot is not redundant because group-healing coverage is explicitly unreliable",
                ),
                matched_exceptions=tuple(matched),
                unknown_exception_contexts=tuple(unknown),
            )

        if matched:
            return self._assessment(
                context,
                policy,
                RotationGameplayPolicyStatus.OVERRIDDEN,
                (
                    "explicit encounter/assignment context overrides the normal DD personal-heal practice",
                ),
                matched_exceptions=tuple(matched),
                unknown_exception_contexts=tuple(unknown),
            )

        reasons = [policy.summary]
        if policy.explanation_requirement:
            reasons.append(policy.explanation_requirement)
        if unknown:
            reasons.append("unrecognized exception context does not establish an override")
        return self._assessment(
            context,
            policy,
            RotationGameplayPolicyStatus.DISFAVORED,
            tuple(reasons),
            unknown_exception_contexts=tuple(unknown),
        )

    @staticmethod
    def _validate_rotation_policy(policy: GameplayPolicy) -> None:
        if "rotation_builder" not in {item.casefold() for item in policy.affected_systems}:
            raise ValueError(
                f"gameplay policy {policy.id!r} is not registered for rotation_builder"
            )
        if policy.default_behavior.casefold() != "disfavor":
            raise ValueError(
                f"gameplay policy {policy.id!r} no longer has the expected disfavor behavior"
            )

    @staticmethod
    def _assessment(
        context: RotationGameplayPolicyContext,
        policy: GameplayPolicy,
        status: RotationGameplayPolicyStatus,
        reasons: tuple[str, ...],
        *,
        matched_exceptions: tuple[str, ...] = (),
        unknown_exception_contexts: tuple[str, ...] = (),
    ) -> RotationGameplayPolicyAssessment:
        return RotationGameplayPolicyAssessment(
            candidate_id=context.candidate_id,
            policy_id=policy.id,
            status=status,
            subject=policy.subject,
            confidence=policy.confidence,
            reasons=reasons,
            personal_heal_skill_slots=context.personal_heal_skill_slots,
            matched_exceptions=matched_exceptions,
            unknown_exception_contexts=unknown_exception_contexts,
        )


def _normalize_role(value: str) -> str:
    role = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    if role in {"dd", "dps", "damage_dealer", "damage"}:
        return "dd"
    return role


def _normalized_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


__all__ = [
    "RotationGameplayPolicyAssessment",
    "RotationGameplayPolicyAssessmentService",
    "RotationGameplayPolicyContext",
    "RotationGameplayPolicyStatus",
]
