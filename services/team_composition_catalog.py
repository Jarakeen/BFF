from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable


COMPOSITION_CATALOG_SCHEMA_VERSION = 1


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _strings(values: Iterable[object] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            rows.append(text)
    return tuple(rows)


@dataclass(frozen=True)
class CompositionSource:
    name: str
    url: str
    retrieved_at: str
    note: str = ""


@dataclass(frozen=True)
class CompositionSlot:
    slot_name: str
    role: str
    preferred_class: str
    alternative_classes: tuple[str, ...] = ()
    responsibilities: tuple[str, ...] = ()
    provider_requirements: tuple[str, ...] = ()
    optional_responsibilities: tuple[str, ...] = ()
    mechanic_jobs: tuple[str, ...] = ()

    @property
    def required_responsibilities(self) -> tuple[str, ...]:
        """Required chair duties retained under the original responsibilities field."""
        return self.responsibilities


@dataclass(frozen=True)
class TeamCompositionTemplate:
    template_id: str
    name: str
    trial_name: str
    goal: str
    difficulty: str
    game_update: str
    catalog_version: str
    sources: tuple[CompositionSource, ...]
    slots: tuple[CompositionSlot, ...]

    def supports(self, *, goal: str, difficulty: str | None = None) -> bool:
        if _clean(goal).casefold() != self.goal.casefold():
            return False
        requested = _clean(difficulty)
        if not requested or not self.difficulty:
            return True
        return requested.casefold() == self.difficulty.casefold()


@dataclass(frozen=True)
class TeamCompositionCatalogSnapshot:
    schema_version: int
    catalog_version: str
    game_update: str
    templates: tuple[TeamCompositionTemplate, ...]


class TeamCompositionCatalog:
    """Load versioned raid-composition evidence.

    This catalog answers which chairs, classes, responsibilities, providers, and
    mechanic jobs a composition wants. It deliberately does not contain players or
    complete builds.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> TeamCompositionCatalogSnapshot:
        if not self.path.is_file():
            return TeamCompositionCatalogSnapshot(
                schema_version=COMPOSITION_CATALOG_SCHEMA_VERSION,
                catalog_version="missing",
                game_update="unresolved",
                templates=(),
            )

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("team composition catalog must be a JSON object")
        schema_version = int(raw.get("schema_version", 0))
        if schema_version != COMPOSITION_CATALOG_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported team composition catalog schema: {schema_version}"
            )
        catalog_version = _clean(raw.get("catalog_version"))
        game_update = _clean(raw.get("game_update"))
        if not catalog_version or not game_update:
            raise ValueError("team composition catalog requires version metadata")

        templates: list[TeamCompositionTemplate] = []
        seen: set[str] = set()
        for item in raw.get("templates") or ():
            if not isinstance(item, dict):
                continue
            template_id = _clean(item.get("template_id"))
            if not template_id:
                raise ValueError("team composition template_id is required")
            key = template_id.casefold()
            if key in seen:
                raise ValueError(f"duplicate team composition template_id: {template_id}")
            seen.add(key)

            sources = tuple(
                CompositionSource(
                    name=_clean(source.get("name")),
                    url=_clean(source.get("url")),
                    retrieved_at=_clean(source.get("retrieved_at")),
                    note=_clean(source.get("note")),
                )
                for source in (item.get("sources") or ())
                if isinstance(source, dict) and _clean(source.get("name"))
            )
            slots = tuple(
                CompositionSlot(
                    slot_name=_clean(slot.get("slot_name")),
                    role=_clean(slot.get("role")),
                    preferred_class=_clean(slot.get("preferred_class")) or "Any class",
                    alternative_classes=_strings(slot.get("alternative_classes") or ()),
                    responsibilities=_strings(
                        slot.get("required_responsibilities")
                        or slot.get("responsibilities")
                        or ()
                    ),
                    provider_requirements=_strings(slot.get("provider_requirements") or ()),
                    optional_responsibilities=_strings(
                        slot.get("optional_responsibilities") or ()
                    ),
                    mechanic_jobs=_strings(slot.get("mechanic_jobs") or ()),
                )
                for slot in (item.get("slots") or ())
                if isinstance(slot, dict) and _clean(slot.get("slot_name"))
            )
            if not slots:
                raise ValueError(
                    f"team composition template {template_id!r} requires at least one slot"
                )

            templates.append(
                TeamCompositionTemplate(
                    template_id=template_id,
                    name=_clean(item.get("name")) or template_id,
                    trial_name=_clean(item.get("trial_name")),
                    goal=_clean(item.get("goal")),
                    difficulty=_clean(item.get("difficulty")),
                    game_update=_clean(item.get("game_update")) or game_update,
                    catalog_version=catalog_version,
                    sources=sources,
                    slots=slots,
                )
            )

        return TeamCompositionCatalogSnapshot(
            schema_version=schema_version,
            catalog_version=catalog_version,
            game_update=game_update,
            templates=tuple(templates),
        )


def find_composition_template(
    snapshot: TeamCompositionCatalogSnapshot,
    *,
    goal: str,
    difficulty: str | None = None,
) -> TeamCompositionTemplate | None:
    return next(
        (
            template
            for template in snapshot.templates
            if template.supports(goal=goal, difficulty=difficulty)
        ),
        None,
    )


def flexible_raid_slots(group_size: int = 12) -> tuple[CompositionSlot, ...]:
    """Return an honest editable skeleton when no evidence-backed comp exists."""

    if group_size == 4:
        labels = (("Tank", "Tank"), ("Healer", "Healer"), ("DD 1", "DD"), ("DD 2", "DD"))
    else:
        labels = (
            ("Main Tank", "Tank"),
            ("Off Tank", "Tank"),
            ("Healer 1", "Healer"),
            ("Healer 2", "Healer"),
            *((f"DD {index}", "DD") for index in range(1, 9)),
        )
    return tuple(
        CompositionSlot(slot_name=name, role=role, preferred_class="Any class")
        for name, role in labels
    )
