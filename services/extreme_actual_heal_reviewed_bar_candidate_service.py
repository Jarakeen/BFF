from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import re

from minmax.build_candidate import BuildCandidate
from minmax.character_progression import CharacterProgression
from minmax.skill_coefficient_repository import ability_entity_id
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.skill_choice_service import load_skill_choices


class ExtremeActualHealReviewedBarCandidateService:
    """Generate bounded active-bar changes for reviewed actual-heal passives.

    This bar-search layer is intentionally narrow. The shared context already has
    verified slot-count math for Mages Guild ``Magicka Controller`` and Fighters
    Guild ``Slayer``. Extreme also owns reviewed Green Balance ``Emerald Moss``
    family math and Nightblade Siphoning ``Soul Siphoner`` generic Healing Done.
    Those reviewed families can therefore justify legal carrier-skill search while
    the canonical context/event layer remains responsible for final scoring.

    Ability-specific cast/proc/slotted effects are *not* inferred here. A skill is
    used only as a legal carrier for the explicitly reviewed line-count passive.
    One deterministic representative per base skill is enough for this objective
    family and avoids pretending that unreviewed morph mechanics have been scored.
    """

    REVIEWED_LINE_IDS = frozenset(
        {"mages_guild", "fighters_guild", "green_balance", "siphoning"}
    )
    PASSIVE_BY_LINE_ID = {
        "mages_guild": "Magicka Controller",
        "fighters_guild": "Slayer",
        "green_balance": "Emerald Moss",
        "siphoning": "Soul Siphoner",
    }

    def __init__(
        self,
        database_path: str | Path,
        *,
        skill_loader: Callable[[str | Path], list[dict]] = load_skill_choices,
    ) -> None:
        self.database_path = Path(database_path)
        self.skill_loader = skill_loader

    @staticmethod
    def _line_id(value: object) -> str:
        text = str(value or "").strip().casefold().replace("'", "")
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @staticmethod
    def _integer(value: object) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _base_id(cls, record: dict) -> int:
        return cls._integer(
            record.get("base_ability_id")
            or record.get("ability_id")
            or record.get("id")
        )

    @classmethod
    def _owned_line_ids(cls, progression: CharacterProgression) -> frozenset[str]:
        return frozenset(
            cls._line_id(line)
            for line in progression.owned_skill_lines
            if cls._line_id(line)
        )

    def reviewed_skill_records(
        self,
        progression: CharacterProgression,
    ) -> tuple[dict, ...]:
        """Return one deterministic active-skill carrier per reviewed base skill."""

        records = list(self.skill_loader(self.database_path))
        owned_line_ids = self._owned_line_ids(progression)
        grouped: dict[int, list[dict]] = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            line = str(record.get("skill_line") or "").strip()
            line_id = self._line_id(line)
            if line_id not in self.REVIEWED_LINE_IDS:
                continue
            if line_id not in owned_line_ids:
                continue
            if self._integer(record.get("is_player")) != 1:
                continue
            if self._integer(record.get("is_passive")) != 0:
                continue
            if self._integer(record.get("base_mechanic")) == 8:
                continue
            name = str(record.get("name") or "").strip()
            base_id = self._base_id(record)
            if not name or base_id <= 0:
                continue
            grouped.setdefault(base_id, []).append(record)

        selected: list[dict] = []
        for base_id, choices in grouped.items():
            # For reviewed line-count passives all morphs contribute equally.
            # Prefer the unmorphed/base record when available so this layer does
            # not silently choose between unreviewed morph-specific mechanics.
            representative = min(
                choices,
                key=lambda record: (
                    self._integer(record.get("morph")) != 0,
                    self._integer(record.get("morph")),
                    str(record.get("name") or "").casefold(),
                    self._integer(record.get("ability_id")),
                ),
            )
            selected.append(dict(representative))

        return tuple(
            sorted(
                selected,
                key=lambda record: (
                    self._line_id(record.get("skill_line")),
                    str(record.get("name") or "").casefold(),
                    self._base_id(record),
                ),
            )
        )

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        progression: CharacterProgression,
        *,
        character_id: str,
        baseline_build_id: str,
        protected_entity_id: str,
        active_bar: str = "front",
    ) -> tuple[BuildCandidate, ...]:
        """Return legal one-slot carrier changes while preserving the scored heal."""

        normalized_entity = str(protected_entity_id or "").strip()
        if not normalized_entity:
            return ()

        records = list(self.skill_loader(self.database_path))
        reviewed = self.reviewed_skill_records(progression)
        if not reviewed:
            return ()

        normalized_bar = str(active_bar or "front").casefold()
        attr = "BackBarSkills" if normalized_bar == "back" else "FrontBarSkills"
        original = list(getattr(baseline_build, attr))
        while len(original) < 6:
            original.append("")
        original = original[:6]

        protected_slots = {
            index
            for index, raw_name in enumerate(original[:5])
            if ability_entity_id(str(raw_name or "").strip()) == normalized_entity
        }
        # The caller is scoring one identified heal. If its physical bar slot
        # cannot be found, fail closed rather than allowing a filler mutation to
        # replace an unrecognized heal.
        if not protected_slots:
            return ()

        base_by_name: dict[str, int] = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            name = str(record.get("name") or "").strip()
            base_id = self._base_id(record)
            if name and base_id > 0:
                base_by_name.setdefault(name.casefold(), base_id)

        result: list[BuildCandidate] = []
        for record in reviewed:
            candidate_name = str(record.get("name") or "").strip()
            candidate_line = str(record.get("skill_line") or "").strip()
            candidate_line_id = self._line_id(candidate_line)
            candidate_base_id = self._base_id(record)
            passive_name = self.PASSIVE_BY_LINE_ID[candidate_line_id]

            for slot_index in range(5):
                if slot_index in protected_slots:
                    continue
                before_name = str(original[slot_index] or "").strip()
                if before_name.casefold() == candidate_name.casefold():
                    continue
                before_base_id = base_by_name.get(before_name.casefold(), 0)
                if before_base_id == candidate_base_id:
                    # Swapping a morph/base record of the same skill does not
                    # change the reviewed line-count passive and would smuggle
                    # unreviewed morph mechanics into this search layer.
                    continue

                other_base_ids = {
                    base_by_name.get(str(name or "").strip().casefold(), 0)
                    for index, name in enumerate(original[:5])
                    if index != slot_index and str(name or "").strip()
                }
                if candidate_base_id in other_base_ids:
                    # Do not slot a second morph/base copy of the same skill.
                    continue

                build = PlayerBuild.from_dict(baseline_build.to_dict())
                skills = list(getattr(build, attr))
                while len(skills) < 6:
                    skills.append("")
                skills = skills[:6]
                skills[slot_index] = candidate_name
                setattr(build, attr, skills)

                result.append(
                    ExtremeCompleteOptimizationService._direct_candidate(
                        build,
                        character_id=character_id,
                        baseline_build_id=baseline_build_id,
                        token=(
                            f"actual-heal-reviewed-bar:{normalized_bar}:"
                            f"{slot_index}:{candidate_line_id}:{candidate_base_id}"
                        ),
                        path=f"{attr}[{slot_index}]",
                        before=before_name,
                        after={
                            "skill": candidate_name,
                            "skill_line": candidate_line,
                            "reviewed_passive": passive_name,
                        },
                        source="extreme:actual-heal:reviewed-bar-passive",
                    )
                )

        return tuple(result)
