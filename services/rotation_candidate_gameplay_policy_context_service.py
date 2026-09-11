from __future__ import annotations

from dataclasses import dataclass

from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import HealRecipientScope, SkillEffectKind
from models.build_model import PlayerBuild
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyContext,
)


_PERSONAL_HEAL_SCOPES = {
    HealRecipientScope.SELF,
    HealRecipientScope.SELF_OR_ALLY,
}


@dataclass(frozen=True)
class RotationCandidatePersonalHealSlotEvidence:
    personal_heal_skill_slots: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class RotationCandidateGameplayPolicyContextService:
    """Project reviewed saved-build slot evidence into gameplay-policy context.

    This service does not infer healing from skill names, role labels, or tooltip prose.
    It resolves each saved bar skill to the canonical skill-rank/component tables and
    only marks a slot as a personal heal when at least one reviewed HEAL component has
    SELF or SELF_OR_ALLY recipient scope. Unknown identity/component/recipient evidence
    fails closed instead of allowing an apparently clean DD bar to pass policy.

    The same build slot evidence applies to every cadence candidate in one generated
    family because rotation candidates alter the plan, not the saved skill loadout.
    Encounter assignment exceptions and healer reliability remain explicit caller
    evidence and are never invented from mechanics.

    ``context_for`` is the recommendation-evidence provider contract. ``evaluate`` is
    retained as a compatibility alias for focused audits and older callers.
    """

    def __init__(
        self,
        *,
        build: PlayerBuild,
        tooltip_service: SavedBuildSkillTooltipService,
        role: str,
        content_type: str,
        reliable_group_healing: bool | None,
        exception_contexts: tuple[str, ...] = (),
    ) -> None:
        self.build = build
        self.tooltip_service = tooltip_service
        self.role = str(role or "").strip()
        self.content_type = str(content_type or "").strip()
        self.reliable_group_healing = reliable_group_healing
        self.exception_contexts = tuple(exception_contexts)
        self._slot_evidence: RotationCandidatePersonalHealSlotEvidence | None = None

    def context_for(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationGameplayPolicyContext:
        evidence = self._slot_evidence
        if evidence is None:
            evidence = self._evaluate_saved_build_slots()
            self._slot_evidence = evidence
        return RotationGameplayPolicyContext(
            candidate_id=candidate.candidate_id,
            role=self.role,
            content_type=self.content_type,
            personal_heal_skill_slots=evidence.personal_heal_skill_slots,
            reliable_group_healing=self.reliable_group_healing,
            exception_contexts=self.exception_contexts,
            personal_heal_slot_evidence_resolved=evidence.resolved,
            personal_heal_slot_unresolved=evidence.unresolved,
        )

    def evaluate(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationGameplayPolicyContext:
        """Compatibility alias for ``context_for``."""

        return self.context_for(candidate)

    def _evaluate_saved_build_slots(self) -> RotationCandidatePersonalHealSlotEvidence:
        selected: list[str] = []
        unresolved: list[str] = []
        for bar_name, skill_name in self._saved_skill_slots():
            slot_label = f"{bar_name}:{skill_name}"
            resolution = self.tooltip_service.coefficients.resolve_name(skill_name)
            if resolution.rank is None:
                messages = tuple(resolution.unresolved) or ("skill identity unresolved",)
                unresolved.extend(f"{slot_label}: {message}" for message in messages)
                continue

            components = tuple(
                self.tooltip_service.components.get_for_skill_rank(
                    resolution.rank.skill_rank_id
                )
            )
            if not components:
                unresolved.append(f"{slot_label}: component classification unavailable")
                continue

            proven_personal = any(
                component.effect_kind is SkillEffectKind.HEAL
                and component.heal_recipient_scope in _PERSONAL_HEAL_SCOPES
                for component in components
            )
            if proven_personal:
                selected.append(slot_label)
                continue

            unresolved_component = False
            for component in components:
                if component.effect_kind is SkillEffectKind.UNKNOWN:
                    unresolved_component = True
                    break
                if (
                    component.effect_kind is SkillEffectKind.HEAL
                    and component.heal_recipient_scope is None
                ):
                    unresolved_component = True
                    break
            if unresolved_component:
                unresolved.append(
                    f"{slot_label}: personal-heal recipient classification unresolved"
                )

        return RotationCandidatePersonalHealSlotEvidence(
            personal_heal_skill_slots=tuple(dict.fromkeys(selected)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _saved_skill_slots(self) -> tuple[tuple[str, str], ...]:
        rows: list[tuple[str, str]] = []
        for bar_name, values in (
            ("front", self.build.FrontBarSkills),
            ("back", self.build.BackBarSkills),
        ):
            for raw in values:
                skill_name = str(raw or "").strip()
                if skill_name:
                    rows.append((bar_name, skill_name))
        return tuple(rows)


__all__ = [
    "RotationCandidateGameplayPolicyContextService",
    "RotationCandidatePersonalHealSlotEvidence",
]
