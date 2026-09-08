from __future__ import annotations

from dataclasses import replace

from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from services.rotation_weapon_attack_projection_service import (
    RotationWeaponAttackProjectionService,
)


class RotationWeaponAttackCandidateSupport:
    """Attach build-derived weapon-attack evidence to final candidate scorecards.

    The wrapped canonical candidate path remains the owner of candidate generation,
    active-bar hard legality, ranking, and selection. This adapter only projects the
    final plan's light/heavy attacks through the exact canonical saved-build weapon
    configuration and promotes unresolved weapon identity into candidate-specific
    unresolved evidence. Known wrong-bar actions remain the existing active-bar hard
    obligation rather than creating a duplicate failure category here.
    """

    def __init__(
        self,
        *,
        canonical_candidates,
        build_adapter: SavedBuildCharacterAdapter,
        projection_service: RotationWeaponAttackProjectionService | None = None,
    ) -> None:
        self.canonical_candidates = canonical_candidates
        self.build_adapter = build_adapter
        self.projection_service = (
            projection_service or RotationWeaponAttackProjectionService()
        )

    @property
    def static_context_service(self):
        return getattr(self.canonical_candidates, "static_context_service", None)

    def run_effects(self, *, player_build, character_id=None, initial_bar="front", **kwargs):
        adaptation = self.build_adapter.adapt(
            player_build,
            character_id=character_id,
        )
        canonical_build = adaptation.build
        unresolved = tuple(
            str(item).strip()
            for item in adaptation.unresolved
            if str(item).strip()
        )
        if canonical_build is None or unresolved:
            return self.canonical_candidates.run_effects(
                player_build=player_build,
                character_id=character_id,
                initial_bar=initial_bar,
                **kwargs,
            )

        resolver = kwargs["scorecard_resolver"]

        def with_weapon_attack_evidence(snapshot):
            scorecard = resolver(snapshot)
            projection = self.projection_service.project(
                build=canonical_build,
                plan=snapshot.plan,
                initial_bar=initial_bar,
            )
            candidate_specific_unresolved = self._dedupe(
                tuple(scorecard.candidate_specific_unresolved)
                + tuple(projection.unresolved)
            )
            return replace(
                scorecard,
                candidate_specific_unresolved=candidate_specific_unresolved,
            )

        kwargs["scorecard_resolver"] = with_weapon_attack_evidence
        return self.canonical_candidates.run_effects(
            player_build=player_build,
            character_id=character_id,
            initial_bar=initial_bar,
            **kwargs,
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            key = value.casefold()
            if not value or key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = ["RotationWeaponAttackCandidateSupport"]
