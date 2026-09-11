from __future__ import annotations

"""Project reviewed encounter evidence into boss-guide timeline and strategy rows.

This is a read-only presentation service. Canonical encounter structure remains
owned by EncounterBossGuideService; this service only supplies reviewed fallback
presentation when the boss guide has no canonical timeline/strategy material.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from services.encounter_evidence import ReconciledEncounterFact, reconcile_encounter_evidence
from services.encounter_evidence_packet import load_encounter_evidence_packet


@dataclass(frozen=True)
class EncounterGuideTimelineRow:
    marker: str
    label: str
    detail: str


@dataclass(frozen=True)
class EncounterGuideStrategyRow:
    mechanic: str
    common_names: tuple[str, ...]
    summary: str
    mitigation: str


@dataclass(frozen=True)
class EncounterGuideEvidenceProjection:
    encounter_id: str
    encounter_name: str
    timeline: tuple[EncounterGuideTimelineRow, ...]
    strategy: tuple[EncounterGuideStrategyRow, ...]
    callouts: tuple[str, ...]
    evidence_rows: int


def _human_key(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _render_value(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value is None:
        return "Unknown"
    if isinstance(value, (list, tuple)):
        return ", ".join(_render_value(item) for item in value)
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if key in {
                "name",
                "ability_id",
                "begin_ability_id",
                "effect_ability_id",
                "cast_ability_id",
                "start_ability_id",
                "damage_ability_id",
                "target_ability_id",
            }:
                continue
            parts.append(f"{_human_key(key)}: {_render_value(item)}")
        return "; ".join(parts)
    text = str(value or "").strip()
    if text and text == text.casefold() and "_" in text:
        return _human_key(text)
    return text


def _mechanic_name(fact: ReconciledEncounterFact) -> str:
    kind = fact.fact_type.casefold()
    key = str(fact.fact_key or "").strip()
    if kind == "mechanic" and isinstance(fact.value, dict):
        return str(fact.value.get("name") or "").strip()
    if kind == "mechanic_state" and fact.value is True and key.casefold().endswith("_exists"):
        return _human_key(key[:-7])
    return ""


def _stem(value: str) -> str:
    return "_".join(
        token
        for token in str(value or "").casefold().replace("-", " ").replace("/", " ").split()
        if token
    )


def _related_detail(name: str, facts: tuple[ReconciledEncounterFact, ...]) -> str:
    stem = _stem(name)
    tokens = tuple(token for token in stem.split("_") if token)
    candidates: list[str] = []
    for fact in facts:
        if not fact.safe_for_review:
            continue
        key = str(fact.fact_key or "").casefold()
        if tokens and not all(token in key for token in tokens[:1]):
            continue
        rendered = _render_value(fact.value)
        if rendered and rendered not in {"Yes", "No"} and rendered not in candidates:
            candidates.append(rendered)
        if len(candidates) >= 3:
            break
    return " • ".join(candidates)


def _timeline_rows(facts: tuple[ReconciledEncounterFact, ...]) -> tuple[EncounterGuideTimelineRow, ...]:
    phases: list[tuple[int, EncounterGuideTimelineRow]] = []
    transitions: list[EncounterGuideTimelineRow] = []

    for fact in facts:
        if not fact.safe_for_review or not isinstance(fact.value, dict):
            continue
        kind = fact.fact_type.casefold()
        value = fact.value
        if kind == "phase":
            label = str(value.get("label") or value.get("name") or _human_key(fact.fact_key)).strip()
            order_raw = value.get("order")
            try:
                order = int(order_raw)
            except (TypeError, ValueError):
                order = 9999
            marker = str(value.get("threshold") or value.get("starts_at") or "").strip()
            if not marker and order != 9999:
                marker = f"P{order}"
            detail = str(value.get("description") or value.get("detail") or "").strip()
            if not detail:
                rendered = _render_value(value)
                detail = rendered or "Reviewed encounter phase evidence."
            phases.append((order, EncounterGuideTimelineRow(marker or "?", label, detail)))
            continue

        if kind not in {"transition", "phase_transition"}:
            continue
        label = str(value.get("label") or value.get("name") or _human_key(fact.fact_key)).strip()
        raw_thresholds = value.get("thresholds")
        if isinstance(raw_thresholds, (list, tuple)):
            markers = [str(item).strip() for item in raw_thresholds if str(item).strip()]
        else:
            marker = str(value.get("threshold") or value.get("starts_at") or "").strip()
            markers = [marker] if marker else []
        detail = str(value.get("description") or value.get("detail") or "").strip()
        if not detail:
            detail = _render_value(value) or "Reviewed encounter transition evidence."
        for marker in markers or ["?"]:
            transitions.append(EncounterGuideTimelineRow(marker, label, detail))

    rows = [row for _order, row in sorted(phases, key=lambda item: item[0])]
    rows.extend(transitions)
    seen: set[tuple[str, str, str]] = set()
    result = []
    for row in rows:
        identity = (row.marker, row.label, row.detail)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(row)
    return tuple(result)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


class EncounterGuideEvidenceProjectionService:
    """Read reviewed encounter evidence for boss-guide fallback presentation."""

    def __init__(self, data_root: Path) -> None:
        self.data_root = Path(data_root)

    def _packets(self, encounter_id: str):
        packets = []
        for folder in ("encounter_evidence", "reference_evidence"):
            root = self.data_root / folder
            if not root.exists():
                continue
            for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
                packet = load_encounter_evidence_packet(path)
                if packet.encounter_id == encounter_id:
                    packets.append(packet)
        return tuple(packets)

    def _common_names(self) -> dict[str, tuple[str, ...]]:
        payload = _load_json(self.data_root / "reference_common_names.json")
        result: dict[str, tuple[str, ...]] = {}
        for row in payload.get("entries", ()) if isinstance(payload.get("entries"), list) else ():
            if not isinstance(row, dict):
                continue
            entry_name = str(row.get("entry_name") or "").strip()
            names = row.get("common_names")
            if entry_name and isinstance(names, list):
                result[entry_name.casefold()] = tuple(str(name).strip() for name in names if str(name).strip())
        return result

    def _mitigations(self) -> dict[str, str]:
        payload = _load_json(self.data_root / "reference_mitigations.json")
        result: dict[str, str] = {}
        for row in payload.get("entries", ()) if isinstance(payload.get("entries"), list) else ():
            if not isinstance(row, dict):
                continue
            entry_name = str(row.get("entry_name") or "").strip()
            mitigation = str(row.get("mitigation") or "").strip()
            if entry_name and mitigation:
                result[entry_name.casefold()] = mitigation
        return result

    def get(self, encounter_id: str, encounter_name: str = "") -> EncounterGuideEvidenceProjection:
        encounter_id = str(encounter_id or "").strip()
        packets = self._packets(encounter_id)
        if not packets:
            return EncounterGuideEvidenceProjection(encounter_id, encounter_name, (), (), (), 0)

        resolved_name = str(encounter_name or packets[0].encounter_name or encounter_id).strip()
        evidence = tuple(row for packet in packets for row in packet.evidence)
        facts = tuple(reconcile_encounter_evidence(evidence))
        timeline = _timeline_rows(facts)

        common_names = self._common_names()
        mitigations = self._mitigations()
        seeds: dict[str, str] = {}
        for fact in facts:
            if not fact.safe_for_review:
                continue
            name = _mechanic_name(fact)
            if name:
                seeds[name.casefold()] = name

        suffix = f" — {resolved_name}".casefold()
        for entry_key in (*mitigations.keys(), *common_names.keys()):
            if entry_key.endswith(suffix):
                mechanic = entry_key[: -len(suffix)].strip()
                if mechanic:
                    seeds.setdefault(mechanic, mechanic.title())

        strategy: list[EncounterGuideStrategyRow] = []
        for _identity, mechanic in sorted(seeds.items(), key=lambda item: item[1].casefold()):
            entry_name = f"{mechanic} — {resolved_name}"
            mitigation = mitigations.get(entry_name.casefold(), "")
            summary = _related_detail(mechanic, facts)
            if not summary:
                summary = "Reviewed encounter mechanic; detailed behavior is not yet summarized."
            strategy.append(
                EncounterGuideStrategyRow(
                    mechanic=mechanic,
                    common_names=common_names.get(entry_name.casefold(), ()),
                    summary=summary,
                    mitigation=mitigation or "Reviewed handling not yet recorded.",
                )
            )

        callouts = tuple(
            f"{row.mechanic}: {row.mitigation}"
            for row in strategy
            if row.mitigation and row.mitigation != "Reviewed handling not yet recorded."
        )[:6]

        return EncounterGuideEvidenceProjection(
            encounter_id=encounter_id,
            encounter_name=resolved_name,
            timeline=timeline,
            strategy=tuple(strategy),
            callouts=callouts,
            evidence_rows=len(evidence),
        )
