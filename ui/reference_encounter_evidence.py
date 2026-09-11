from __future__ import annotations

"""Presentation-only projection for reviewed encounter evidence.

Canonical encounter rows remain preferred. This helper exists for source-model
mismatches such as Dreadsail Reef's Lylanar + Turlassil pair and source records
whose boss backing exists but does not carry the reviewed trial mechanic.
Nothing here promotes evidence into canonical encounter truth.
"""

from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

from engine.config import get_data_dir
from services.encounter_evidence import ReconciledEncounterFact, reconcile_encounter_evidence
from services.encounter_evidence_packet import load_encounter_evidence_packet
from services.encounter_repository import EncounterRepository
from ui.reference_data_model import ReferenceEntry


_MECHANIC_FACT_TYPES = frozenset({"mechanic", "mechanic_detail", "mechanic_state"})

# Source packets deliberately split encounter knowledge into small facts. Some
# mechanic families use different nouns across those facts, so literal stem
# matching alone cannot join the evidence for a human-readable Reference entry.
# This map is presentation metadata only: it groups already-reviewed evidence and
# does not promote or reinterpret any value as canonical encounter truth.
_RELATED_MECHANIC_TOKENS: dict[tuple[str, str], tuple[str, ...]] = {
    ("lylanar_turlassil", "destructive_ember"): ("destructive_ember", "dome", "sphere", "overload"),
    ("lylanar_turlassil", "piercing_hailstone"): ("piercing_hailstone", "dome", "sphere", "overload"),
    ("lylanar_turlassil", "firebrand"): ("firebrand", "brand"),
    ("lylanar_turlassil", "frostbrand"): ("frostbrand", "brand"),
    ("reef_guardian", "acid_reflux"): ("acid_reflux", "acid_pool"),
    ("reef_guardian", "replication"): ("replication",),
    ("reef_guardian", "heartburn"): ("heartburn", "reef_heart"),
    ("tideborn_taleria", "rapid_deluge"): ("rapid_deluge", "deluge"),
    ("tideborn_taleria", "crashing_wave"): ("crashing_wave",),
    ("tideborn_taleria", "maelstrom"): ("maelstrom",),
    ("tideborn_taleria", "coral_slam"): ("coral_slam", "rising_tide"),
    ("tideborn_taleria", "arcing_slash"): ("arcing_slash", "soaked_wound"),
}


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


def _canonical_mechanic_entry_names(data_root: Path) -> frozenset[str]:
    """Return display identities already represented by canonical mechanics."""

    try:
        repository = EncounterRepository.from_data_root(data_root)
    except (OSError, ValueError):
        return frozenset()

    names: set[str] = set()
    for encounter_id in repository.encounter_ids():
        try:
            encounter = repository.get(encounter_id)
        except (OSError, ValueError, LookupError):
            continue
        for mechanic in encounter.mechanics:
            if mechanic.name:
                names.add(f"{mechanic.name} — {encounter.name}".casefold())
    return frozenset(names)


def _render_text(value: str) -> str:
    """Humanize source-schema tokens without changing stored evidence values."""

    text = str(value or "")
    if text and text == text.casefold() and "_" in text:
        return text.replace("_", " ").title()
    return text


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
    if isinstance(value, str):
        return _render_text(value)
    return str(value)


def _title_from_exists_key(fact_key: str) -> str:
    suffix = "_exists"
    key = str(fact_key or "").strip()
    if not key.casefold().endswith(suffix):
        return ""
    stem = key[: -len(suffix)].strip("_")
    return stem.replace("_", " ").title() if stem else ""


def _mechanic_stem(fact: ReconciledEncounterFact) -> str:
    kind = fact.fact_type.casefold()
    key = str(fact.fact_key or "").strip().casefold()
    if kind == "mechanic_state" and fact.value is True and key.endswith("_exists"):
        return key[:-7].strip("_")
    if kind == "mechanic" and isinstance(fact.value, dict) and fact.value.get("name"):
        return key
    return ""


def _named_mechanic_fact(fact: ReconciledEncounterFact) -> str:
    kind = fact.fact_type.casefold()
    if kind not in _MECHANIC_FACT_TYPES:
        return ""
    if isinstance(fact.value, dict):
        return str(fact.value.get("name") or "").strip()
    if kind == "mechanic_state" and fact.value is True:
        return _title_from_exists_key(fact.fact_key)
    return ""


def _fact_label(fact: ReconciledEncounterFact) -> str:
    return str(fact.fact_key or "").replace("_", " ").strip().title()


def _evidence_lines(fact: ReconciledEncounterFact) -> tuple[str, ...]:
    lines = []
    for row in fact.evidence:
        locator = f" • {row.source_locator}" if row.source_locator else ""
        update = f" • {row.game_update}" if row.game_update else ""
        lines.append(
            f"{row.source_type}: {row.source_name}{locator}{update} • {row.confidence} confidence"
        )
    return tuple(lines)


def _key_matches_token(key: str, token: str) -> bool:
    if key == token:
        return True
    marker = f"_{token}_"
    padded = f"_{key}_"
    return key.startswith(f"{token}_") or key.endswith(f"_{token}") or marker in padded


def _related_facts(
    encounter_id: str,
    seed: ReconciledEncounterFact,
    facts: Iterable[ReconciledEncounterFact],
) -> tuple[ReconciledEncounterFact, ...]:
    """Find split reviewed evidence that belongs with one visible mechanic."""

    stem = _mechanic_stem(seed)
    if not stem:
        return ()
    tokens = _RELATED_MECHANIC_TOKENS.get((str(encounter_id).casefold(), stem), (stem,))
    result = []
    for fact in facts:
        if fact is seed:
            continue
        key = str(fact.fact_key or "").strip().casefold()
        if any(_key_matches_token(key, token) for token in tokens):
            result.append(fact)
    return tuple(result)


def _entry_from_fact(
    packet,
    fact: ReconciledEncounterFact,
    all_facts: Iterable[ReconciledEncounterFact] = (),
) -> ReferenceEntry | None:
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

    evidence = list(_evidence_lines(fact))
    for related_fact in _related_facts(packet.encounter_id, fact, all_facts):
        if related_fact.safe_for_review:
            related_rendered = _render_value(related_fact.value)
            if related_rendered:
                details.append((f"Evidence • {_fact_label(related_fact)}", related_rendered))
        elif related_fact.status == "conflicting":
            details.append(
                (
                    f"Evidence conflict • {_fact_label(related_fact)}",
                    f"Unresolved: {related_fact.distinct_values} reviewed values across "
                    f"{related_fact.distinct_sources} source families/records.",
                )
            )
        evidence.extend(_evidence_lines(related_fact))

    return ReferenceEntry(
        name=f"{name} — {packet.encounter_name}",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("ENCOUNTER", "REVIEWED EVIDENCE"),
        summary=(
            "Reviewed source evidence exists for this encounter mechanic, but this exact mechanic "
            "is not yet represented by a canonical encounter mechanic record."
        ),
        details=tuple(dict.fromkeys(details)),
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


def _merge_entries(existing: ReferenceEntry, entry: ReferenceEntry) -> ReferenceEntry:
    return replace(
        existing,
        details=tuple(dict.fromkeys((*existing.details, *entry.details))),
        related=tuple(dict.fromkeys((*existing.related, *entry.related))),
        used_by=tuple(dict.fromkeys((*existing.used_by, *entry.used_by))),
        evidence=tuple(dict.fromkeys((*existing.evidence, *entry.evidence))),
    )


def _evidence_paths(data_root: Path) -> tuple[Path, ...]:
    """Return canonical encounter packets plus supplemental Reference-only packets."""

    roots = (data_root / "encounter_evidence", data_root / "reference_evidence")
    paths: list[Path] = []
    for root in roots:
        if root.exists():
            paths.extend(root.glob("*.json"))
    return tuple(sorted(paths, key=lambda item: (item.parent.name.casefold(), item.name.casefold())))


def _load_evidence_entries(
    data_root: Path,
    *,
    skip_backed_encounters: bool,
    suppress_canonical_mechanics: bool,
) -> tuple[ReferenceEntry, ...]:
    backed_ids = _boss_ids(data_root) if skip_backed_encounters else frozenset()
    represented = _canonical_mechanic_entry_names(data_root) if suppress_canonical_mechanics else frozenset()
    entries: dict[str, ReferenceEntry] = {}

    packets: dict[str, list] = {}
    for path in _evidence_paths(data_root):
        packet = load_encounter_evidence_packet(path)
        packets.setdefault(packet.encounter_id, []).append(packet)

    for packet_group in packets.values():
        encounter_id = packet_group[0].encounter_id
        if encounter_id in backed_ids:
            continue
        combined_evidence = tuple(
            row
            for packet in packet_group
            for row in packet.evidence
        )
        facts = tuple(reconcile_encounter_evidence(combined_evidence))
        packet = packet_group[0]
        for fact in facts:
            entry = _entry_from_fact(packet, fact, facts)
            if entry is None:
                continue
            identity = entry.name.casefold()
            if identity in represented:
                continue
            existing = entries.get(identity)
            entries[identity] = entry if existing is None else _merge_entries(existing, entry)

    return tuple(sorted(entries.values(), key=lambda entry: (entry.name.casefold(), entry.name)))


def _canonical_evidence_details(entry: ReferenceEntry) -> tuple[tuple[str, str], ...]:
    details = []
    for label, value in entry.details:
        if label in {"Authority", "Encounter", "Content ID"}:
            continue
        if label.startswith("Evidence •") or label.startswith("Evidence conflict •"):
            details.append((label, value))
        else:
            details.append((f"Reviewed evidence • {label}", value))
    return tuple(details)


def enrich_reference_entries_with_encounter_evidence(
    entries: Iterable[ReferenceEntry],
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Augment canonical Reference entries and append only unmatched evidence entries."""

    root = data_root or get_data_dir()
    evidence_entries = _load_evidence_entries(
        root,
        skip_backed_encounters=False,
        suppress_canonical_mechanics=False,
    )
    by_name = {entry.name.casefold(): entry for entry in evidence_entries}
    result: list[ReferenceEntry] = []
    represented: set[str] = set()

    for entry in entries:
        identity = entry.name.casefold()
        represented.add(identity)
        evidence_entry = by_name.get(identity)
        if evidence_entry is None:
            result.append(entry)
            continue
        result.append(
            replace(
                entry,
                details=tuple(
                    dict.fromkeys((*entry.details, *_canonical_evidence_details(evidence_entry)))
                ),
                related=tuple(dict.fromkeys((*entry.related, *evidence_entry.related))),
                used_by=tuple(dict.fromkeys((*entry.used_by, *evidence_entry.used_by))),
                evidence=tuple(dict.fromkeys((*entry.evidence, *evidence_entry.evidence))),
            )
        )

    result.extend(
        evidence_entry
        for evidence_entry in evidence_entries
        if evidence_entry.name.casefold() not in represented
    )
    return tuple(result)


def load_reviewed_encounter_evidence_entries(
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Project safe reviewed mechanic evidence missing from canonical Reference."""

    root = data_root or get_data_dir()
    return _load_evidence_entries(
        root,
        skip_backed_encounters=False,
        suppress_canonical_mechanics=True,
    )


def load_unbacked_encounter_evidence_entries(
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Compatibility loader for evidence packets with no boss backing record."""

    root = data_root or get_data_dir()
    return _load_evidence_entries(
        root,
        skip_backed_encounters=True,
        suppress_canonical_mechanics=False,
    )
