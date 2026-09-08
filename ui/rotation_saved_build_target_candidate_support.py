from __future__ import annotations

from dataclasses import replace

from minmax.rotation_action_target_legality import (
    RotationActionTargetAssessment,
    RotationActionTargetAssessor,
    RotationTargetStateWindow,
)
from minmax.rotation_plan import RotationActionKind
from services.rotation_saved_build_action_target_service import (
    RotationSavedBuildActionTargetService,
)


class RotationSavedBuildTargetCandidateSupport:
    """Attach conservative saved-build target evidence to final candidates.

    The wrapped canonical candidate path remains the owner of candidate generation,
    ranking, and selection. This adapter resolves exact saved-skill target identity
    once, then audits every stabilized final candidate only when explicit target-state
    windows are supplied.

    Enemy, Self, and Ground requirements are enforced as known target-legality hard
    obligations. Area, Cone, blank, unsupported, or ambiguous saved target evidence
    remains unresolved and becomes candidate-specific only when the final plan uses
    that action in a target-relevant evaluation. No tooltip inference or role-based
    target assumptions are introduced here.
    """

    def __init__(
        self,
        *,
        canonical_candidates,
        target_service: RotationSavedBuildActionTargetService | None = None,
        target_assessor: RotationActionTargetAssessor | None = None,
    ) -> None:
        self.canonical_candidates = canonical_candidates
        self.target_service = target_service or RotationSavedBuildActionTargetService()
        self.target_assessor = target_assessor or RotationActionTargetAssessor()

    @property
    def static_context_service(self):
        return getattr(self.canonical_candidates, "static_context_service", None)

    def run_effects(
        self,
        *,
        player_build,
        target_state_windows=(),
        **kwargs,
    ):
        windows = tuple(target_state_windows)
        if not windows:
            return self.canonical_candidates.run_effects(
                player_build=player_build,
                **kwargs,
            )

        evidence = self.target_service.resolve(player_build)
        resolver = kwargs["scorecard_resolver"]

        def with_target_evidence(snapshot):
            scorecard = resolver(snapshot)
            target_assessment = scorecard.target_assessment

            if evidence.target_requirements:
                automatic = self.target_assessor.assess(
                    snapshot.plan,
                    evidence.target_requirements,
                    windows,
                )
                target_assessment = RotationActionTargetAssessment(
                    self._dedupe_objects(
                        tuple(getattr(scorecard, "target_violations", ()))
                        + automatic.violations
                    )
                )

            used_names = {
                str(action.name).strip().casefold()
                for action in snapshot.plan.actions
                if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
                and action.name
                and str(action.name).strip()
            }
            relevant_unresolved = tuple(
                f"canonical action target unresolved for used action: {name}"
                for name in evidence.unresolved_action_names
                if name.casefold() in used_names
            )
            candidate_specific_unresolved = self._dedupe_strings(
                tuple(scorecard.candidate_specific_unresolved)
                + relevant_unresolved
            )

            return replace(
                scorecard,
                target_assessment=target_assessment,
                candidate_specific_unresolved=candidate_specific_unresolved,
            )

        kwargs["scorecard_resolver"] = with_target_evidence
        return self.canonical_candidates.run_effects(
            player_build=player_build,
            **kwargs,
        )

    @staticmethod
    def _dedupe_objects(values: tuple[object, ...]) -> tuple:
        ordered: list[object] = []
        for value in values:
            if value not in ordered:
                ordered.append(value)
        return tuple(ordered)

    @staticmethod
    def _dedupe_strings(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            key = value.casefold()
            if not value or key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)


__all__ = ["RotationSavedBuildTargetCandidateSupport"]
