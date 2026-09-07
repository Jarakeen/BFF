from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.character_build import CharacterBuild, IllegalBuildError
from minmax.rotation_plan import RotationActionKind
from minmax.skill_coefficient_repository import ability_entity_id
from services.rotation_action_occupancy_legality_service import RotationActionOccupancyRule
from services.rotation_skill_timing_evidence_service import (
    RotationSkillTimingEvidence,
    RotationSkillTimingEvidenceService,
)


@dataclass(frozen=True)
class RotationBuildTimingPolicy:
    """Explicit occupancy-blocking semantics layered on canonical skill timing.

    Canonical ability data proves cast/channel duration. It does not by itself prove
    ESO global-cooldown, weave, bar-swap, interrupt, or cancellation semantics, so
    callers must provide those blocking relationships explicitly.
    """

    skill_blocked_action_kinds: tuple[RotationActionKind, ...] = ()
    ultimate_blocked_action_kinds: tuple[RotationActionKind, ...] = ()


@dataclass(frozen=True)
class RotationBuildTimingProjection:
    """Canonical timing evidence/rules available to one mechanically legal build."""

    build_name: str
    evidence: tuple[RotationSkillTimingEvidence, ...]
    rules: tuple[RotationActionOccupancyRule, ...]
    unresolved: tuple[str, ...] = ()


class RotationBuildTimingProjectionService:
    """Project canonical cast/channel timing for every skill slotted on a build.

    Scope is deliberately role-neutral. Class skills, weapon skills, guild/world/
    alliance skills, and Ultimates all use the same canonical skill identity path.
    CharacterBuild legality is enforced first so impossible class-line or weapon-line
    combinations never become timing evidence.

    Passive-derived timing modifiers are not inferred here. When canonical passive
    effect identities describe timing changes, they should be resolved upstream and
    applied as an explicit timing-modifier layer rather than parsed from passive text.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.timing_service = RotationSkillTimingEvidenceService(database_path)

    def project(
        self,
        *,
        build: CharacterBuild,
        policy: RotationBuildTimingPolicy,
    ) -> RotationBuildTimingProjection:
        violations = tuple(build.validate())
        if violations:
            raise IllegalBuildError(violations)

        evidence: list[RotationSkillTimingEvidence] = []
        rules: list[RotationActionOccupancyRule] = []
        unresolved: list[str] = []
        seen_evidence: set[tuple[RotationActionKind, str]] = set()
        seen_rules: set[tuple[RotationActionKind, str]] = set()

        for bar in build.bars():
            for slot in bar.slots:
                skill_id = ability_entity_id(slot.skill_id)
                if not skill_id:
                    unresolved.append(
                        f"{bar.bar_id.value} bar has a slotted skill without a stable skill identity"
                    )
                    continue

                action_kind = (
                    RotationActionKind.ULTIMATE
                    if slot.is_ultimate
                    else RotationActionKind.SKILL
                )
                resolution = self.timing_service.resolve_skill(skill_id)
                if resolution.evidence is None:
                    detail = "; ".join(resolution.unresolved) or "canonical timing unresolved"
                    unresolved.append(
                        f"{bar.bar_id.value} bar {action_kind.value} {slot.skill_id!r}: {detail}"
                    )
                    continue

                item = resolution.evidence
                evidence_key = (action_kind, item.skill_id)
                if evidence_key not in seen_evidence:
                    seen_evidence.add(evidence_key)
                    evidence.append(item)

                occupancy = item.occupancy_seconds
                if occupancy is None:
                    continue

                blocked = (
                    policy.ultimate_blocked_action_kinds
                    if action_kind is RotationActionKind.ULTIMATE
                    else policy.skill_blocked_action_kinds
                )
                rule_key = (action_kind, self._stable_name(item.name))
                if rule_key in seen_rules:
                    continue
                seen_rules.add(rule_key)
                rules.append(
                    RotationActionOccupancyRule(
                        action_kind=action_kind,
                        action_name=item.name,
                        occupancy_seconds=occupancy,
                        blocked_action_kinds=tuple(blocked),
                        source=item.source,
                    )
                )

        return RotationBuildTimingProjection(
            build_name=build.name,
            evidence=tuple(evidence),
            rules=tuple(rules),
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _stable_name(value: object) -> str:
        return "".join(character for character in str(value or "").casefold() if character.isalnum())

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = [
    "RotationBuildTimingPolicy",
    "RotationBuildTimingProjection",
    "RotationBuildTimingProjectionService",
]
