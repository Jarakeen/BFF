from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path

from minmax.skill_coefficient_repository import ability_entity_id


_REQUIRED_EXECUTABLE_FIELDS = (
    "reviewed_interval_seconds",
    "first_tick_offset_seconds",
    "refresh_boundary",
    "magnitude_policy",
)


@dataclass(frozen=True)
class RotationDDPeriodicRuntimeSemanticsReviewEntry:
    """Non-executable reviewed evidence for one DD periodic component.

    This record may be incomplete. It exists so reviewed partial facts can be kept
    without promoting them into executable runtime semantics prematurely.
    """

    skill_entity_id: str
    coefficient_number: int
    duration_seconds: float | None = None
    reviewed_interval_seconds: float | None = None
    first_tick_offset_seconds: float | None = None
    refresh_boundary: str | None = None
    magnitude_policy: str | None = None
    successive_hit_multiplier: float | None = None
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        entity_id = ability_entity_id(self.skill_entity_id)
        if not entity_id:
            raise ValueError("periodic semantics review requires skill identity")
        object.__setattr__(self, "skill_entity_id", entity_id)
        if int(self.coefficient_number) <= 0:
            raise ValueError("periodic semantics review coefficient_number must be positive")
        object.__setattr__(self, "coefficient_number", int(self.coefficient_number))

        for field_name in (
            "duration_seconds",
            "reviewed_interval_seconds",
            "first_tick_offset_seconds",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            number = float(value)
            if not math.isfinite(number) or number < 0 or (
                field_name == "reviewed_interval_seconds" and number <= 0
            ):
                raise ValueError(f"{field_name} must be finite and valid")
            object.__setattr__(self, field_name, number)

        multiplier = self.successive_hit_multiplier
        if multiplier is not None:
            multiplier = float(multiplier)
            if not math.isfinite(multiplier) or multiplier <= 0:
                raise ValueError("successive_hit_multiplier must be finite and positive")
            object.__setattr__(self, "successive_hit_multiplier", multiplier)

        evidence = tuple(
            dict.fromkeys(str(item).strip() for item in self.evidence if str(item).strip())
        )
        if not evidence:
            raise ValueError("periodic semantics review requires evidence provenance")
        object.__setattr__(self, "evidence", evidence)

    @property
    def unresolved_executable_fields(self) -> tuple[str, ...]:
        return tuple(
            field_name
            for field_name in _REQUIRED_EXECUTABLE_FIELDS
            if getattr(self, field_name) is None
        )

    @property
    def executable_complete(self) -> bool:
        return not self.unresolved_executable_fields


class RotationDDPeriodicRuntimeSemanticsReviewService:
    """Load non-executable, dimension-by-dimension DD periodic review evidence."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path)
            if path is not None
            else Path(__file__).resolve().parents[1]
            / "data"
            / "rotation_dd_periodic_runtime_semantics_review.json"
        )

    def load(self) -> tuple[RotationDDPeriodicRuntimeSemanticsReviewEntry, ...]:
        if not self.path.exists():
            return ()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("DD periodic semantics review schema_version must be 1")
        rows = payload.get("entries", [])
        if not isinstance(rows, list):
            raise ValueError("DD periodic semantics review entries must be a list")

        entries: list[RotationDDPeriodicRuntimeSemanticsReviewEntry] = []
        seen: set[tuple[str, int]] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"DD periodic semantics review entry {index} must be an object")
            try:
                entry = RotationDDPeriodicRuntimeSemanticsReviewEntry(
                    skill_entity_id=str(row["skill_entity_id"]),
                    coefficient_number=int(row["coefficient_number"]),
                    duration_seconds=row.get("duration_seconds"),
                    reviewed_interval_seconds=row.get("reviewed_interval_seconds"),
                    first_tick_offset_seconds=row.get("first_tick_offset_seconds"),
                    refresh_boundary=(
                        None if row.get("refresh_boundary") is None else str(row["refresh_boundary"])
                    ),
                    magnitude_policy=(
                        None if row.get("magnitude_policy") is None else str(row["magnitude_policy"])
                    ),
                    successive_hit_multiplier=row.get("successive_hit_multiplier"),
                    evidence=tuple(row.get("evidence", ())),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid DD periodic semantics review entry {index}: {exc}") from exc
            key = (entry.skill_entity_id, entry.coefficient_number)
            if key in seen:
                raise ValueError(
                    "duplicate DD periodic semantics review for "
                    f"{entry.skill_entity_id} coefficient {entry.coefficient_number}"
                )
            seen.add(key)
            entries.append(entry)
        return tuple(entries)

    def by_component(self) -> dict[tuple[str, int], RotationDDPeriodicRuntimeSemanticsReviewEntry]:
        return {
            (entry.skill_entity_id, entry.coefficient_number): entry
            for entry in self.load()
        }


__all__ = [
    "RotationDDPeriodicRuntimeSemanticsReviewEntry",
    "RotationDDPeriodicRuntimeSemanticsReviewService",
]
