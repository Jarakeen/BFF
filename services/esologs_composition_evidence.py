from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from models.top_team_model import TopTeamPlayer, TopTeamResult


_ROLE_ALIASES = {
    "tank": "Tank",
    "tanks": "Tank",
    "healer": "Healer",
    "healers": "Healer",
    "heal": "Healer",
    "dps": "DD",
    "dd": "DD",
    "damage": "DD",
    "damage dealer": "DD",
    "damage dealers": "DD",
}


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_role(value: object) -> str:
    return _ROLE_ALIASES.get(_clean(value).casefold(), "")


def _slot_name(role: str, ordinal: int) -> str:
    if role == "Tank":
        if ordinal == 1:
            return "Main Tank"
        if ordinal == 2:
            return "Off Tank"
        return f"Tank {ordinal}"
    if role == "Healer":
        return f"Healer {ordinal}"
    if role == "DD":
        return f"DD {ordinal}"
    return f"Slot {ordinal}"


def _ordered_counter(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(counter.items(), key=lambda item: (-item[1], item[0].casefold())))


@dataclass(frozen=True)
class ObservedCompositionSlot:
    slot_name: str
    role: str
    preferred_class: str
    alternative_classes: tuple[str, ...]
    sample_count: int
    class_counts: tuple[tuple[str, int], ...]
    observed_gear_sets: tuple[tuple[str, int], ...] = ()
    observed_abilities: tuple[tuple[str, int], ...] = ()

    @property
    def confidence(self) -> float:
        if not self.sample_count or not self.class_counts:
            return 0.0
        return self.class_counts[0][1] / self.sample_count


@dataclass(frozen=True)
class EsoLogsCompositionEvidence:
    trial_name: str
    sample_count: int
    encounter_names: tuple[str, ...]
    report_fights: tuple[str, ...]
    slots: tuple[ObservedCompositionSlot, ...]

    def slot(self, slot_name: str) -> ObservedCompositionSlot | None:
        target = _clean(slot_name).casefold()
        return next(
            (slot for slot in self.slots if slot.slot_name.casefold() == target),
            None,
        )


class EsoLogsCompositionEvidenceService:
    """Aggregate observed ranked-team snapshots into composition evidence.

    This service does not infer buffs, mechanics, or ideal builds. It only summarizes
    what the supplied ESO Logs team snapshots actually contain: role-chair class
    frequency plus observed gear-set and ability frequency. That makes it safe to use
    as evidence in Comp Builder without turning popularity into canonical truth.

    ``TopTeamResult`` is the native input, but ``load_snapshots`` also accepts a small
    interchange format so external grabbers can feed the same aggregation boundary.
    """

    def aggregate(
        self,
        results: Iterable[TopTeamResult],
        *,
        trial_name: str | None = None,
    ) -> EsoLogsCompositionEvidence:
        rows = tuple(result for result in results if result.Players)
        resolved_trial = _clean(trial_name) or self._common_trial(rows)

        class_counts: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
        gear_counts: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
        ability_counts: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
        slot_samples: Counter[tuple[str, int]] = Counter()

        encounters: list[str] = []
        reports: list[str] = []
        seen_encounters: set[str] = set()
        seen_reports: set[str] = set()

        for result in rows:
            encounter = _clean(result.EncounterName)
            encounter_key = encounter.casefold()
            if encounter and encounter_key not in seen_encounters:
                seen_encounters.add(encounter_key)
                encounters.append(encounter)

            if result.ReportCode:
                report_ref = f"{result.ReportCode}#{int(result.FightId)}"
                if report_ref not in seen_reports:
                    seen_reports.add(report_ref)
                    reports.append(report_ref)

            ordinals: Counter[str] = Counter()
            for player in result.Players:
                role = _normalize_role(player.Role)
                if not role:
                    continue
                ordinals[role] += 1
                key = (role, ordinals[role])
                slot_samples[key] += 1

                class_name = _clean(player.ClassName or player.EsoClass)
                if class_name:
                    class_counts[key][class_name] += 1

                for set_name in player.GearSets:
                    text = _clean(set_name)
                    if text:
                        gear_counts[key][text] += 1

                for ability in player.Abilities:
                    text = _clean(ability)
                    if text:
                        ability_counts[key][text] += 1

        role_order = {"Tank": 0, "Healer": 1, "DD": 2}
        keys = sorted(
            slot_samples,
            key=lambda key: (role_order.get(key[0], 99), key[1]),
        )

        slots: list[ObservedCompositionSlot] = []
        for role, ordinal in keys:
            key = (role, ordinal)
            ordered_classes = _ordered_counter(class_counts[key])
            preferred = ordered_classes[0][0] if ordered_classes else ""
            alternatives = tuple(name for name, _count in ordered_classes[1:])
            slots.append(
                ObservedCompositionSlot(
                    slot_name=_slot_name(role, ordinal),
                    role=role,
                    preferred_class=preferred,
                    alternative_classes=alternatives,
                    sample_count=int(slot_samples[key]),
                    class_counts=ordered_classes,
                    observed_gear_sets=_ordered_counter(gear_counts[key]),
                    observed_abilities=_ordered_counter(ability_counts[key]),
                )
            )

        return EsoLogsCompositionEvidence(
            trial_name=resolved_trial,
            sample_count=len(rows),
            encounter_names=tuple(encounters),
            report_fights=tuple(reports),
            slots=tuple(slots),
        )

    @staticmethod
    def _common_trial(results: tuple[TopTeamResult, ...]) -> str:
        counter: Counter[str] = Counter()
        display: dict[str, str] = {}
        for result in results:
            name = _clean(result.TrialName)
            if not name:
                continue
            key = name.casefold()
            counter[key] += 1
            display.setdefault(key, name)
        if not counter:
            return ""
        winner = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
        return display[winner]

    def load_snapshots(self, path: str | Path) -> tuple[TopTeamResult, ...]:
        """Load external/native top-team snapshots without depending on one grabber.

        Accepted roots:
        - a single TopTeamResult-like object
        - a list of such objects
        - an object containing ``teams``, ``results``, or ``snapshots``

        Common snake_case aliases are normalized before using ``TopTeamResult``.
        Unknown metadata is ignored rather than silently converted into evidence.
        """

        source = Path(path)
        if not source.is_file():
            return ()
        raw = json.loads(source.read_text(encoding="utf-8"))

        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            nested = None
            for key in ("teams", "results", "snapshots"):
                value = raw.get(key)
                if isinstance(value, list):
                    nested = value
                    break
            items = nested if nested is not None else [raw]
        else:
            raise ValueError("ESO Logs composition snapshots must be a JSON object or list")

        results: list[TopTeamResult] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized = self._normalize_result_payload(item)
            result = TopTeamResult.from_dict(normalized)
            if result.Players:
                results.append(result)
        return tuple(results)

    @staticmethod
    def _normalize_result_payload(item: dict) -> dict:
        players = item.get("Players", item.get("players", []))
        return {
            "TrialName": item.get("TrialName", item.get("trial_name", item.get("trial", ""))),
            "EncounterName": item.get(
                "EncounterName",
                item.get("encounter_name", item.get("encounter", "")),
            ),
            "ReportCode": item.get(
                "ReportCode",
                item.get("report_code", item.get("report", "")),
            ),
            "FightId": item.get(
                "FightId",
                item.get("fight_id", item.get("fightID", 0)),
            ),
            "Players": players if isinstance(players, list) else [],
        }
