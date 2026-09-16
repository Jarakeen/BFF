from __future__ import annotations

"""Expand H1 gear-package candidates through legal inactive-bar setup actions.

The wrapped package service remains authoritative for gear generation. This adapter
only adds physically legal setup-action bar variants for reviewed gear mechanics
that require a cast before the scored heal. Candidate scoring remains canonical.

When a caller does not provide the scored ``active_bar``, both front/back setup
orientations are emitted. Canonical H1 condition resolution later activates a setup
condition only when its witness is present on the bar opposite the actual scored bar.
"""

from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.gear_stat_inputs import GearStatInputResolver
from services.extreme_actual_heal_setup_action_legality_service import (
    GRANTS_RESOLVE,
    HAS_CAST_OR_CHANNEL_TIME,
    IS_ASSAULT_ABILITY,
    REDUCES_TARGET_RESISTANCE,
    ExtremeActualHealSetupActionLegalityService,
)
from services.extreme_actual_heal_setup_action_materialization_service import (
    ExtremeActualHealSetupActionMaterializationService,
)
from services.extreme_player_skill_candidate_service import ExtremePlayerSkillLegalityContext


_REVIEWED_SETUP_SETS = (
    ("Seventh Legion Brute", GRANTS_RESOLVE, "resolve"),
    ("Soulshine", HAS_CAST_OR_CHANNEL_TIME, "cast-channel"),
    ("Powerful Assault", IS_ASSAULT_ABILITY, "assault"),
    ("Ravager", REDUCES_TARGET_RESISTANCE, "resistance-reduction"),
)


class ExtremeActualHealSetupActionPackageAdapter:
    """Decorate gear-package candidates with reviewed setup-bar variants."""

    def __init__(
        self,
        delegate,
        legality: ExtremeActualHealSetupActionLegalityService,
        *,
        active_bar_default: str | None = None,
    ) -> None:
        self.delegate = delegate
        self.legality = legality
        self.active_bar_default = active_bar_default

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    @staticmethod
    def _bar_attr(bar: str) -> str:
        return "BackBarSkills" if str(bar or "front").strip().casefold() == "back" else "FrontBarSkills"

    @staticmethod
    def _normalized_bar(value: object) -> str | None:
        key = str(value or "").strip().casefold()
        return key if key in {"front", "back"} else None

    def _orientations(self, active_bar: str | None) -> tuple[str, ...]:
        explicit = self._normalized_bar(active_bar)
        if explicit is not None:
            return (explicit,)
        default = self._normalized_bar(self.active_bar_default)
        if default is not None:
            return (default,)
        return ("front", "back")

    def expand_candidates(
        self,
        candidates: tuple[BuildCandidate, ...],
        *,
        active_bar: str | None = None,
    ) -> tuple[BuildCandidate, ...]:
        expanded: list[BuildCandidate] = []
        orientations = self._orientations(active_bar)

        for candidate in candidates:
            expanded.append(candidate)
            build = candidate.candidate_build
            legality_context = ExtremePlayerSkillLegalityContext(
                equipped_class_lines=tuple(build.ClassSkillLines or ()),
                vampire=bool(build.Vampire),
                werewolf=bool(build.Werewolf),
                transformed_form=str(build.TransformedForm or "").strip() or None,
            )

            for scored_bar in orientations:
                counts = GearStatInputResolver.equipped_set_counts(build, active_bar=scored_bar)
                for set_name, capability, token in _REVIEWED_SETUP_SETS:
                    if int(counts.get(set_name, 0)) < 5:
                        continue
                    witness = self.legality.witness(capability, legality_context)
                    if not witness.proven:
                        continue

                    setup_bar = "back" if scored_bar == "front" else "front"
                    setup_attr = self._bar_attr(setup_bar)
                    before_bar = list(getattr(build, setup_attr))
                    for placement in ExtremeActualHealSetupActionMaterializationService.variants(
                        build,
                        witness,
                        active_bar=scored_bar,
                    ):
                        if not placement.materialized:
                            continue
                        after_bar = list(getattr(placement.build, setup_attr))
                        if after_bar == before_bar:
                            continue
                        slot = int(placement.slot_index or 0)
                        change = BuildChange.from_values(
                            path=f"{setup_attr}[{slot}]",
                            before=before_bar[slot] if slot < len(before_bar) else "",
                            after=after_bar[slot],
                            source=f"extreme:actual-heal:setup-action:{token}",
                        )
                        expanded.append(
                            BuildCandidate.from_build(
                                character_id=candidate.character_id,
                                baseline_build_id=candidate.baseline_build_id,
                                candidate_id=(
                                    f"{candidate.candidate_id}:setup-{token}:{scored_bar}:{slot}"
                                ),
                                candidate_build=placement.build,
                                changes=(*candidate.changes, change),
                                candidate_source=f"{candidate.candidate_source}+setup-{token}",
                                evaluation_state=candidate.evaluation_state,
                                unresolved=candidate.unresolved,
                            )
                        )

        unique = {candidate.candidate_id: candidate for candidate in expanded}
        return tuple(unique[key] for key in sorted(unique))

    def build_candidates(self, baseline_build, *args, **kwargs):
        active_bar = kwargs.get("active_bar")
        candidates = tuple(self.delegate.build_candidates(baseline_build, *args, **kwargs))
        return self.expand_candidates(candidates, active_bar=active_bar)


__all__ = ["ExtremeActualHealSetupActionPackageAdapter"]
