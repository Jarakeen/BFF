from __future__ import annotations

"""Presentation-only projection for reviewed encounter evidence without boss backing.

Canonical encounter rows remain preferred. This helper exists for source-model
mismatches such as Dreadsail Reef's Lylanar + Turlassil pair: raid operations
model one encounter while the raw boss corpus stores the brothers separately.
Only reconciled, non-conflicting mechanic evidence with an explicit human name is
projected. Nothing here promotes evidence into canonical encounter truth.
"""

from pathlib import Path
from typing import Any

from engine.config import get_data_dir
from services.encounter_evidence import ReconciledEncounterFact, reconcile_encounter_evidence
from services.encounter_evidence_packet import load_encounter_evidence_packet
from ui.reference_data_model import ReferenceEntry


_MECHANIC_FACT_TYPES = frozenset({"mechanic", "mechanic_detail"})


def _boss_ids(data_root: Path) -> frozenset[str]:
    root = data_root / "eso_info" / "bosses"
    ids: set[str] = set()
    for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
        try:
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict):
            identity = str(payload.get("id") or "").strip()
            if identity:
                ids.add(identity)
    return frozenset(ids)


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
            if key in {"name", "ability_id", "begin_ability_id", "effect_ability_id", "cast_ability_id"}:
                continue
            parts.append(f"{str(key).replace('_', ' ').title()}: {_render_value(item)}")
        return "; ".join(parts)
    return str(value)


def _named_mechanic_fact(fact: ReconciledEncounterFact) -> str:
    if fact.fact_type.casefold() not in _MECHANIC_FACT_TYPES:
        return ""
    if not isinstance(fact.value, dict):
        return ""
    return str(fact.value.get("name") or "").strip()


def _entry_from_fact(packet, fact: ReconciledEncounterFact) -> ReferenceEntry | None:
    name = _named_mechanic_fact(fact)
    if not name or not fact.safe_for_review:
        return None

    details = [
        ("Authority", "Reviewed encounter evidence; not yet canonical encounter truth"),
        ("Encounter", packet.encounter_name),
        ("Content ID", packet.content_id or "Not recorded"),
        ("Evidence status", fact.status.replace("_", " ").title()),
        ("Fact type", fact.fact_type.replace("_", " ").title()),
        ("Evidence sources", str(fact.distinct_sources)),
    ]
    rendered = _render_value(fact.value)
    if rendered:
        details.append(("Reviewed details", rendered))

    evidence = []
    for row in fact.evidence:
        locator = f" • {row.source_locator}" if row.source_locator else ""
        update = f" • {row.game_update}" if row.game_update else ""
        evidence.append(
            f"{row.source_type}: {row.source_name}{locator}{update} • {row.confidence} confidence"
        )

    return ReferenceEntry(
        name=f"{name} — {packet.encounter_name}",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("ENCOUNTER", "REVIEWED EVIDENCE"),
        summary=(
            "Reviewed source evidence exists for this encounter mechanic, but the paired/source "
            "encounter does not yet have a canonical boss-backed mechanic record."
        ),
        details=tuple(details),
        related=(packet.encounter_name,),
        death_note=(
            "Use the reviewed mechanic evidence as context only. Death analysis should prefer a "
            "canonical mechanic record when one becomes available."
        ),
        field_note=(
            "Evidence-only reference entry. It is deliberately visible so source-model gaps do "
            "not erase useful raid knowledge, but it is not promoted into combat math or encounter truth."
        ),
        used_by=("Combat Reference", "Encounter Research"),
        evidence=tuple(dict.fromkeys(evidence)),
    )


def load_unbacked_encounter_evidence_entries(
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    root = data_root or get_data_dir()
    backed_ids = _boss_ids(root)
    evidence_root = root / "encounter_evidence"
    entries: list[ReferenceEntry] = []

    for path in sorted(evidence_root.glob("*.json"), key=lambda item: item.name.casefold()):
        packet = load_encounter_evidence_packet(path)
        if packet.encounter_id in backed_ids:
            continue
        for fact in reconcile_encounter_evidence(packet.evidence):
            entry = _entry_from_fact(packet, fact)
            if entry is not None:
                entries.append(entry)

    return tuple(
        sorted(entries, key=lambda entry: (entry.name.casefold(), entry.name))
    )
