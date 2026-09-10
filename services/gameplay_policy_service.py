from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir


DEFAULT_GAMEPLAY_POLICY = get_data_dir() / "gameplay_policy" / "endgame_pve.json"


@dataclass(frozen=True)
class GameplayPolicy:
    id: str
    role: str
    content_type: tuple[str, ...]
    default_behavior: str
    subject: str
    confidence: str
    summary: str
    exceptions: tuple[str, ...] = ()
    affected_systems: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()
    override_contexts: tuple[str, ...] = ()
    modeling_requirements: tuple[str, ...] = ()
    explanation_requirement: str | None = None

    def applies_to(self, *, role: str | None = None, content_type: str | None = None) -> bool:
        normalized_role = str(role or "").strip().casefold()
        normalized_content = str(content_type or "").strip().casefold()

        role_matches = not normalized_role or self.role in {"any", normalized_role}
        content_matches = not normalized_content or normalized_content in self.content_type
        return role_matches and content_matches


class GameplayPolicyService:
    """Read-only access to contextual ESO play-practice policy.

    Policy lives above canonical mechanics. It may rank, discourage, require, or
    explain a mechanically legal option, but it must not redefine the underlying
    ESO mechanic itself.
    """

    def __init__(self, path: str | Path = DEFAULT_GAMEPLAY_POLICY) -> None:
        self.path = Path(path)
        self._policies = self._load(self.path)

    @staticmethod
    def _load(path: Path) -> tuple[GameplayPolicy, ...]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        policies = payload.get("policies")
        if not isinstance(policies, list):
            raise ValueError("gameplay policy registry requires a policies list")

        loaded: list[GameplayPolicy] = []
        seen_ids: set[str] = set()
        for raw in policies:
            if not isinstance(raw, dict):
                raise ValueError("gameplay policy entries must be objects")
            policy_id = str(raw.get("id") or "").strip()
            if not policy_id:
                raise ValueError("gameplay policy requires a non-empty id")
            if policy_id in seen_ids:
                raise ValueError(f"duplicate gameplay policy id: {policy_id}")
            seen_ids.add(policy_id)

            loaded.append(
                GameplayPolicy(
                    id=policy_id,
                    role=str(raw.get("role") or "any").strip().casefold(),
                    content_type=tuple(
                        str(value).strip().casefold()
                        for value in raw.get("content_type", [])
                        if str(value).strip()
                    ),
                    default_behavior=str(raw.get("default_behavior") or "").strip(),
                    subject=str(raw.get("subject") or "").strip(),
                    confidence=str(raw.get("confidence") or "").strip(),
                    summary=str(raw.get("summary") or "").strip(),
                    exceptions=GameplayPolicyService._tuple_field(raw, "exceptions"),
                    affected_systems=GameplayPolicyService._tuple_field(raw, "affected_systems"),
                    rationale=GameplayPolicyService._tuple_field(raw, "rationale"),
                    override_contexts=GameplayPolicyService._tuple_field(raw, "override_contexts"),
                    modeling_requirements=GameplayPolicyService._tuple_field(raw, "modeling_requirements"),
                    explanation_requirement=(
                        str(raw["explanation_requirement"]).strip()
                        if raw.get("explanation_requirement")
                        else None
                    ),
                )
            )
        return tuple(loaded)

    @staticmethod
    def _tuple_field(raw: dict, key: str) -> tuple[str, ...]:
        value = raw.get(key, [])
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ValueError(f"gameplay policy field {key!r} must be a list")
        return tuple(str(item).strip() for item in value if str(item).strip())

    def all(self) -> tuple[GameplayPolicy, ...]:
        return self._policies

    def get(self, policy_id: str) -> GameplayPolicy | None:
        target = str(policy_id or "").strip()
        return next((policy for policy in self._policies if policy.id == target), None)

    def require(self, policy_id: str) -> GameplayPolicy:
        policy = self.get(policy_id)
        if policy is None:
            raise KeyError(f"unknown gameplay policy: {policy_id}")
        return policy

    def find(
        self,
        *,
        role: str | None = None,
        content_type: str | None = None,
        subject: str | None = None,
        affected_system: str | None = None,
    ) -> tuple[GameplayPolicy, ...]:
        normalized_subject = str(subject or "").strip().casefold()
        normalized_system = str(affected_system or "").strip().casefold()

        def matches(policy: GameplayPolicy) -> bool:
            if not policy.applies_to(role=role, content_type=content_type):
                return False
            if normalized_subject and policy.subject.casefold() != normalized_subject:
                return False
            if normalized_system and normalized_system not in {
                value.casefold() for value in policy.affected_systems
            }:
                return False
            return True

        return tuple(policy for policy in self._policies if matches(policy))

    def ids(self) -> tuple[str, ...]:
        return tuple(policy.id for policy in self._policies)


def policy_ids(policies: Iterable[GameplayPolicy]) -> tuple[str, ...]:
    return tuple(policy.id for policy in policies)
