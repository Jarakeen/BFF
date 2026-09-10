from __future__ import annotations

"""Presentation-only projection for reviewed encounter evidence.

Canonical encounter rows remain preferred. This helper exists for source-model
mismatches such as Dreadsail Reef's Lylanar + Turlassil pair and source records
whose boss backing exists but does not carry the reviewed trial mechanic.
Nothing here promotes evidence into canonical encounter truth.
"""

from pathlib import Path
from typing import Any

from engine.config import get_data_dir
from services.encounter_evidence import ReconciledEncounterFact, reconcile_encounter_evidence
from services.encounter_evidence_packet import load_encounter_evidence_packet
from services.encounter_repository import EncounterRepository
from ui.reference_data_model import ReferenceEntry


_MECHANIC_FACT_TYPES = frozenset({"mechanic", "mechanic_detail", "mechanic_state"})


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


def _title_from_exists_key(fact_key: str) -> str:
    suffix = "_exists"
    key = str(fact_key or "").strip()
    if not key.casefold().endswith(suffix):
        return ""
    stem = key[: -len(suffix)].strip("_")
    return stem.replace("_", " ").title() if stem else ""


def _named_mechanic_fact(fact: ReconciledEncounterFact) -> str:
    kind = fact.fact_type.casefold()
    if kind not in _MECHANIC_FACT_TYPES:
        return ""
    if isinstance(fact.value, dict):
        return str(fact.value.get("name") or "").strip()
    if kind == "mechanic_state" and fact.value is True:
        return _title_from_exists_key(fact.fact_key)
    return ""


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
            "Reviewed source evidence exists for this encounter mechanic, but this exact mechanic "
            "is not yet represented by a canonical encounter mechanic record."
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


def _load_evidence_entries(
    data_root: Path,
    *,
    skip_backed_encounters: bool,
    suppress_canonical_mechanics: bool,
) -> tuple[ReferenceEntry, ...]:
    backed_ids = _boss_ids(data_root) if skip_backed_encounters else frozenset()
    represented = _canonical_mechanic_entry_names(data_root) if suppress_canonical_mechanics else frozenset()
    evidence_root = data_root / "encounter_evidence"
    entries: dict[str, ReferenceEntry] = {}

    for path in sorted(evidence_root.glob("*.json"), key=lambda item: item.name.casefold()):
        packet = load_encounter_evidence_packet(path)
        if packet.encounter_id in backed_ids:
            continue
        for fact in reconcile_encounter_evidence(packet.evidence):
            entry = _entry_from_fact(packet, fact)
            if entry is None:
                continue
            identity = entry.name.casefold()
            if identity in represented:
                continue
            existing = entries.get(identity)
            if existing is None:
                entries[identity] = entry
                continue
            entries[identity] = ReferenceEntry(
                name=existing.name,
                entry_type=existing.entry_type,
                source_scope=existing.source_scope,
                tags=existing.tags,
                summary=existing.summary,
                details=tuple(dict.fromkeys((*existing.details, *entry.details))),
                related=tuple(dict.fromkeys((*existing.related, *entry.related))),
                death_note=existing.death_note,
                field_note=existing.field_note,
                used_by=tuple(dict.fromkeys((*existing.used_by, *entry.used_by))),
                evidence=tuple(dict.fromkeys((*existing.evidence, *entry.evidence))),
            )

    return tuple(sorted(entries.values(), key=lambda entry: (entry.name.casefold(), entry.name)))


def load_reviewed_encounter_evidence_entries(
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Project safe reviewed mechanic evidence missing from canonical Reference.

    A boss backing record by itself is not enough to suppress evidence; only an
    already-represented canonical mechanic with the same display identity does.
    """

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
