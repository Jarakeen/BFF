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
from services.reference_research_enrichment_service import (
    ReferenceResearchEnrichmentService,
    ReviewedReferenceFact,
)


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
    brief: tuple[str, ...]
    role_impact: tuple[str, ...]
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


def _stem_tokens(value: str) -> tuple[str, ...]:
    normalized = str(value or "").casefold().replace("-", " ").replace("/", " ")
    return tuple(token for token in normalized.split() if token)


def _related_detail(name: str, facts: tuple[ReconciledEncounterFact, ...]) -> str:
    tokens = _stem_tokens(name)
    candidates: list[str] = []
    for fact in facts:
        if not fact.safe_for_review:
            continue
        key = str(fact.fact_key or "").casefold()
        if tokens and not any(token in key for token in tokens):
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


def _overview_brief_rows(facts: tuple[ReconciledEncounterFact, ...]) -> tuple[str, ...]:
    """Render compact reviewed fight-shape facts for the Encounters Overview."""
    rows: list[str] = []
    for fact in facts:
        if not fact.safe_for_review or not isinstance(fact.value, dict):
            continue
        kind = fact.fact_type.casefold()
        value = fact.value

        if kind == "damage_window":
            label = _human_key(fact.fact_key)
            triggers = value.get("trigger_health_percent")
            if isinstance(triggers, (list, tuple)):
                markers = [f"{item}%" for item in triggers if isinstance(item, (int, float))]
            else:
                markers = []
            details: list[str] = []
            if value.get("boss_targetable") is False or value.get("boss_damageable") is False:
                details.append("boss is untargetable and cannot be damaged")
            if value.get("adds_active") is True:
                details.append("adds are active")
            if value.get("raid_damage_active") is True:
                details.append("raid damage continues")
            attacks = value.get("flight_attacks")
            if isinstance(attacks, (list, tuple)) and attacks:
                rendered_attacks = ", ".join(_human_key(str(item)) for item in attacks if str(item).strip())
                if rendered_attacks:
                    details.append(f"incoming: {rendered_attacks}")
            if value.get("final_beam_requires_block") is True:
                details.append("final beam must be blocked")
            prefix = f"At {', '.join(markers)}" if markers else label
            body = "; ".join(details) or _render_value(value)
            if body:
                rows.append(f"{prefix}: {body}.")
            continue

        if kind == "add_group":
            members = value.get("members")
            if not isinstance(members, (list, tuple)) or not members:
                continue
            names = ", ".join(str(item).strip() for item in members if str(item).strip())
            trigger = _human_key(str(value.get("trigger") or ""))
            line = f"Adds: {names}"
            if trigger:
                line += f" during {trigger}"
            if value.get("exact_count_resolved") is False:
                line += "; exact count remains unresolved"
            rows.append(line + ".")

    seen: set[str] = set()
    result: list[str] = []
    for row in rows:
        if row in seen:
            continue
        seen.add(row)
        result.append(row)
    return tuple(result[:6])


def _fact_subject(fact_key: str) -> str:
    key = str(fact_key or "").strip().casefold()
    for suffix in ("_core_behavior", "_behavior", "_targeting", "_detail"):
        if key.endswith(suffix):
            key = key[: -len(suffix)]
            break
    if "_behavior_" in key:
        key = key.split("_behavior_", 1)[0]
    return _human_key(key)


def _role_impact_rows(facts: tuple[ReconciledEncounterFact, ...]) -> tuple[str, ...]:
    """Derive role implications only from explicit structured reviewed fields."""
    rows: list[str] = []
    for fact in facts:
        if not fact.safe_for_review or not isinstance(fact.value, dict):
            continue
        kind = fact.fact_type.casefold()
        value = fact.value

        if str(value.get("target") or "").casefold() == "taunt_target":
            subject = _fact_subject(fact.fact_key) or "Taunt-target mechanic"
            details: list[str] = []
            if value.get("leaves_acid_pools") is True:
                details.append("leaves persistent pools")
            if value.get("applies_stacking_acid_vulnerability") is True:
                details.append("applies stacking vulnerability")
            suffix = f"; {', '.join(details)}" if details else ""
            rows.append(f"Tanks — {subject} targets the taunt target{suffix}.")

        if kind == "damage_window":
            boss_unavailable = value.get("boss_targetable") is False or value.get("boss_damageable") is False
            if boss_unavailable and value.get("adds_active") is True:
                rows.append(
                    "Damage Dealers — Reviewed boss downtime has an unavailable boss target while adds remain active."
                )
            if value.get("raid_damage_active") is True:
                rows.append(
                    "Healers — Reviewed boss downtime still has active raid damage; healing pressure does not pause with boss damage."
                )

    seen: set[str] = set()
    result: list[str] = []
    for row in rows:
        if row in seen:
            continue
        seen.add(row)
        result.append(row)
    return tuple(result[:6])


def _research_facts_for_encounter(encounter_name: str) -> tuple[ReviewedReferenceFact, ...]:
    suffix = f" — {str(encounter_name or '').strip()}".casefold()
    if suffix == " — ":
        return ()
    return tuple(
        fact
        for fact in ReferenceResearchEnrichmentService().all()
        if fact.entry_name.casefold().endswith(suffix)
    )


def _research_strategy_rows(
    research_facts: tuple[ReviewedReferenceFact, ...],
) -> tuple[EncounterGuideStrategyRow, ...]:
    grouped: dict[str, list[ReviewedReferenceFact]] = {}
    display_names: dict[str, str] = {}
    for fact in research_facts:
        mechanic = fact.entry_name.split(" — ", 1)[0].strip()
        if not mechanic:
            continue
        key = mechanic.casefold()
        grouped.setdefault(key, []).append(fact)
        display_names.setdefault(key, mechanic)

    rows: list[EncounterGuideStrategyRow] = []
    for key in sorted(grouped, key=lambda item: display_names[item].casefold()):
        facts = grouped[key]
        handling = next(
            (
                fact.value
                for fact in facts
                if fact.label.casefold() in {"handling", "response", "priority"}
                and str(fact.value or "").strip()
            ),
            "",
        )
        summary_parts = [
            f"{fact.label}: {fact.value}"
            for fact in facts
            if fact.label.casefold() not in {"handling", "response", "priority"}
            and str(fact.value or "").strip()
        ][:3]
        if not summary_parts:
            summary_parts = [
                f"{fact.label}: {fact.value}"
                for fact in facts
                if str(fact.value or "").strip()
            ][:3]
        rows.append(
            EncounterGuideStrategyRow(
                mechanic=display_names[key],
                common_names=(),
                summary=" • ".join(summary_parts)
                or "Reviewed secondary encounter research is available.",
                mitigation=handling or "Reviewed handling not yet recorded.",
            )
        )
    return tuple(rows)


def _research_brief_rows(
    research_rows: tuple[EncounterGuideStrategyRow, ...],
) -> tuple[str, ...]:
    return tuple(
        f"{row.mechanic}: {row.summary}"
        for row in research_rows[:6]
    )


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
        result: dict[str, str] = {}
        for path in sorted(self.data_root.glob("reference_mitigations*.json"), key=lambda item: item.name.casefold()):
            payload = _load_json(path)
            rows = payload.get("entries", ()) if isinstance(payload.get("entries"), list) else ()
            for row in rows:
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
        resolved_name = str(
            encounter_name
            or (packets[0].encounter_name if packets else "")
            or encounter_id
        ).strip()
        research_facts = _research_facts_for_encounter(resolved_name)
        research_strategy = _research_strategy_rows(research_facts)

        if not packets and not research_facts:
            return EncounterGuideEvidenceProjection(encounter_id, resolved_name, (), (), (), (), (), 0)

        evidence = tuple(row for packet in packets for row in packet.evidence)
        facts = tuple(reconcile_encounter_evidence(evidence))
        timeline = _timeline_rows(facts)
        brief = _overview_brief_rows(facts)
        role_impact = _role_impact_rows(facts)

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

        research_by_name = {row.mechanic.casefold(): row for row in research_strategy}
        for key, row in research_by_name.items():
            seeds.setdefault(key, row.mechanic)

        strategy: list[EncounterGuideStrategyRow] = []
        for identity, mechanic in sorted(seeds.items(), key=lambda item: item[1].casefold()):
            entry_name = f"{mechanic} — {resolved_name}"
            mitigation = mitigations.get(entry_name.casefold(), "")
            summary = _related_detail(mechanic, facts)
            research_row = research_by_name.get(identity)
            if not summary and research_row is not None:
                summary = research_row.summary
            if not mitigation and research_row is not None:
                mitigation = research_row.mitigation
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

        if not brief and research_strategy:
            brief = _research_brief_rows(research_strategy)

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
            brief=brief,
            role_impact=role_impact,
            evidence_rows=len(evidence) + len(research_facts),
        )
