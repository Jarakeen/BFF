from __future__ import annotations

"""Expand H1 gear-package candidates through legal inactive-bar setup actions.

The wrapped package service remains authoritative for gear generation. This adapter
only adds physically legal setup-action bar variants for reviewed gear mechanics
that require a cast before the scored heal. Candidate scoring remains canonical.
"""

from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.gear_stat_inputs import GearStatInputResolver
from services.extreme_actual_heal_setup_action_legality_service import (
    GRANTS_RESOLVE,
    ExtremeActualHealSetupActionLegalityService,
)
from services.extreme_actual_heal_setup_action_materialization_service import (
    ExtremeActualHealSetupActionMaterializationService,
)
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext


_SEVENTH_LEGION_BRUTE = "Seventh Legion Brute"


class ExtremeActualHealSetupActionPackageAdapter:
    """Decorate a gear-package candidate service with reviewed setup-bar variants."""

    def __init__(
        self,
        delegate,
        legality: ExtremeActualHealSetupActionLegalityService,
        *,
        active_bar_default: str = "front",
    ) -> None:
        self.delegate = delegate
        self.legality = legality
        self.active_bar_default = active_bar_default

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    @staticmethod
    def _bar_attr(bar: str) -> str:
        return "BackBarSkills" if str(bar or "front").strip().casefold() == "back" else "FrontBarSkills"

    def build_candidates(self, baseline_build, *args, **kwargs):
        candidates = tuple(self.delegate.build_candidates(baseline_build, *args, **kwargs))
        active_bar = str(kwargs.get("active_bar", self.active_bar_default) or "front").strip().casefold()
        if active_bar not in {"front", "back"}:
            active_bar = "front"

        expanded: list[BuildCandidate] = []
        for candidate in candidates:
            expanded.append(candidate)
            build = candidate.candidate_build
            counts = GearStatInputResolver.equipped_set_counts(build, active_bar=active_bar)
            if int(counts.get(_SEVENTH_LEGION_BRUTE, 0)) < 5:
                continue

            legality_context = ExtremePlayerSkillLegalityContext(
                equipped_class_lines=tuple(build.ClassSkillLines or ()),
                vampire=bool(build.Vampire),
                werewolf=bool(build.Werewolf),
                transformed_form=str(build.TransformedForm or "").strip() or None,
            )
            witness = self.legality.witness(GRANTS_RESOLVE, legality_context)
            if not witness.proven:
                continue

            setup_attr = self._bar_attr("back" if active_bar == "front" else "front")
            before_bar = list(getattr(build, setup_attr))
            for placement in ExtremeActualHealSetupActionMaterializationService.variants(
                build,
                witness,
                active_bar=active_bar,
            ):
                if not placement.materialized:
                    continue
                after_bar = list(getattr(placement.build, setup_attr))
                if after_bar == before_bar:
                    # Existing witness: the original candidate already owns the legal setup.
                    continue
                slot = int(placement.slot_index or 0)
                change = BuildChange.from_values(
                    path=f"{setup_attr}[{slot}]",
                    before=before_bar[slot] if slot < len(before_bar) else "",
                    after=after_bar[slot],
                    source="extreme:actual-heal:setup-action:resolve",
                )
                expanded.append(
                    BuildCandidate.from_build(
                        character_id=candidate.character_id,
                        baseline_build_id=candidate.baseline_build_id,
                        candidate_id=f"{candidate.candidate_id}:setup-resolve:{slot}",
                        candidate_build=placement.build,
                        changes=(*candidate.changes, change),
                        candidate_source=f"{candidate.candidate_source}+setup-resolve",
                        evaluation_state=candidate.evaluation_state,
                        unresolved=candidate.unresolved,
                    )
                )

        unique = {candidate.candidate_id: candidate for candidate in expanded}
        return tuple(unique[key] for key in sorted(unique))


__all__ = ["ExtremeActualHealSetupActionPackageAdapter"]
