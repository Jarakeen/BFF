from __future__ import annotations

"""Reusable build-copy and role-template persistence for canonical saved builds.

A saved Build remains owned by one Character. Reuse never copies player identity,
character progression, team assignment, or readiness. Templates keep a role-level
base payload plus optional class overlays so class-specific state is not silently
applied to a different class.
"""

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from models.build_model import BuildRoster, PlayerBuild


_IDENTITY_FIELDS = {
    "Name", "Gamertag", "CharacterId", "BuildId", "ReadyForRaid",
}
_CLASS_OVERLAY_FIELDS = {
    "FrontBarSkills", "BackBarSkills", "ClassSkillLines", "ClassMasteryAbilityIds",
    "ScribedSkills", "ScribedSkillRecipes",
}
_SKILL_BAR_FIELDS = ("FrontBarSkills", "BackBarSkills")


@dataclass(frozen=True)
class BuildTemplateRecord:
    template_id: str
    name: str
    role: str
    source_class: str
    base_payload: dict[str, Any]
    class_overlays: dict[str, dict[str, Any]]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "role": self.role,
            "source_class": self.source_class,
            "base_payload": deepcopy(self.base_payload),
            "class_overlays": deepcopy(self.class_overlays),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BuildTemplateRecord":
        return cls(
            template_id=str(value.get("template_id") or "").strip(),
            name=str(value.get("name") or "").strip(),
            role=str(value.get("role") or "").strip(),
            source_class=str(value.get("source_class") or "").strip(),
            base_payload=deepcopy(value.get("base_payload") or {}),
            class_overlays=deepcopy(value.get("class_overlays") or {}),
            notes=str(value.get("notes") or "").strip(),
        )


@dataclass(frozen=True)
class BuildReuseResult:
    build: PlayerBuild
    warnings: tuple[str, ...] = ()


class BuildReuseService:
    SCHEMA_VERSION = 1

    def __init__(self, template_path: Path):
        self.template_path = Path(template_path)

    @staticmethod
    def _stable_id(name: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"bff:build-template:{name.strip().casefold()}"))

    @staticmethod
    def _clean_payload(build: PlayerBuild, *, include_variants: bool, include_notes: bool) -> dict[str, Any]:
        payload = deepcopy(build.to_dict())
        for field in _IDENTITY_FIELDS:
            payload.pop(field, None)
        payload["ReadyForRaid"] = False
        payload["BuildName"] = build.BuildName.strip()
        if not include_variants:
            payload["ContextVariants"] = []
            payload["BossLoadouts"] = []
        if not include_notes:
            payload["Notes"] = ""
        return payload

    @staticmethod
    def _normalized_bar(value: object) -> list[str]:
        bar = [str(item or "").strip() for item in list(value or [])[:6]]
        return (bar + [""] * 6)[:6]

    @classmethod
    def _derive_shared_skill_core(
        cls,
        base_payload: dict[str, Any],
        overlays: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        """Promote same-slot skills shared by every class overlay into the role base.

        This is deliberately evidence-based rather than a guessed class taxonomy. If
        the Warden and Arcanist healer overlays both put Combat Prayer in slot 1, that
        slot becomes part of the reusable healer core. Different skills remain in
        their class overlays.
        """
        if len(overlays) < 2:
            return deepcopy(base_payload), deepcopy(overlays)

        result_base = deepcopy(base_payload)
        result_overlays = deepcopy(overlays)
        for field in _SKILL_BAR_FIELDS:
            bars = [cls._normalized_bar(overlay.get(field)) for overlay in result_overlays.values()]
            common = [""] * 6
            for index in range(6):
                values = [bar[index] for bar in bars]
                nonempty = [value for value in values if value]
                if nonempty and len(nonempty) == len(values) and len({value.casefold() for value in nonempty}) == 1:
                    common[index] = nonempty[0]
            if any(common):
                base_bar = cls._normalized_bar(result_base.get(field))
                for index, value in enumerate(common):
                    if value:
                        base_bar[index] = value
                result_base[field] = base_bar
                for overlay in result_overlays.values():
                    overlay_bar = cls._normalized_bar(overlay.get(field))
                    for index, value in enumerate(common):
                        if value and overlay_bar[index].casefold() == value.casefold():
                            overlay_bar[index] = ""
                    overlay[field] = overlay_bar
        return result_base, result_overlays

    @classmethod
    def _apply_overlay(cls, base_payload: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(base_payload)
        for field, value in overlay.items():
            if field in _SKILL_BAR_FIELDS:
                base_bar = cls._normalized_bar(result.get(field))
                overlay_bar = cls._normalized_bar(value)
                result[field] = [overlay_bar[index] or base_bar[index] for index in range(6)]
            else:
                result[field] = deepcopy(value)
        return result

    def load_templates(self) -> tuple[BuildTemplateRecord, ...]:
        if not self.template_path.exists():
            return ()
        try:
            raw = json.loads(self.template_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ()
        rows = raw.get("templates") if isinstance(raw, dict) else None
        if not isinstance(rows, list):
            return ()
        result = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            record = BuildTemplateRecord.from_dict(row)
            if record.template_id and record.name:
                result.append(record)
        return tuple(sorted(result, key=lambda item: (item.role.casefold(), item.name.casefold())))

    def _save_templates(self, rows: list[BuildTemplateRecord]) -> None:
        self.template_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "templates": [row.to_dict() for row in rows],
        }
        temp = self.template_path.with_suffix(self.template_path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.template_path)

    def save_template_from_build(
        self,
        build: PlayerBuild,
        *,
        template_name: str,
        include_variants: bool = True,
        include_notes: bool = True,
    ) -> BuildTemplateRecord:
        name = str(template_name or "").strip()
        if not name:
            raise ValueError("Template name is required")
        payload = self._clean_payload(build, include_variants=include_variants, include_notes=include_notes)
        source_class = build.EsoClass.strip()
        overlay = {field: deepcopy(payload.pop(field, None)) for field in _CLASS_OVERLAY_FIELDS if field in payload}
        template_id = self._stable_id(name)
        rows = list(self.load_templates())
        existing = next((row for row in rows if row.template_id == template_id), None)

        # Reusing the same template name with another class adds/replaces that
        # class overlay while preserving the first role-level base. This lets a
        # healer template accumulate Warden, Arcanist, Templar, etc. overlays.
        if existing is not None:
            if existing.role and build.Role.strip() and existing.role.casefold() != build.Role.strip().casefold():
                raise ValueError(
                    f"Template {name!r} is already a {existing.role} template; choose a different name for {build.Role.strip() or 'this role'}."
                )
            overlays = deepcopy(existing.class_overlays)
            if source_class:
                overlays[source_class] = overlay
            base_payload, overlays = self._derive_shared_skill_core(existing.base_payload, overlays)
            notes = existing.notes
            source_text = f"{build.Name or build.Gamertag} • {build.BuildName}".strip(" •")
            if source_text and source_text not in notes:
                notes = " | ".join(piece for piece in (notes, f"Overlay from {source_text}") if piece)
            record = BuildTemplateRecord(
                template_id=existing.template_id,
                name=existing.name,
                role=existing.role or build.Role.strip(),
                source_class=existing.source_class or source_class,
                base_payload=base_payload,
                class_overlays=overlays,
                notes=notes,
            )
            rows = [row for row in rows if row.template_id != template_id]
        else:
            record = BuildTemplateRecord(
                template_id=template_id,
                name=name,
                role=build.Role.strip(),
                source_class=source_class,
                base_payload=payload,
                class_overlays={source_class: overlay} if source_class else {},
                notes=(f"Created from {build.Name or build.Gamertag} • {build.BuildName}".strip(" •")),
            )

        rows.append(record)
        self._save_templates(rows)
        return record

    def delete_template(self, template_id: str) -> bool:
        wanted = str(template_id or "").strip()
        rows = list(self.load_templates())
        kept = [row for row in rows if row.template_id != wanted]
        if len(kept) == len(rows):
            return False
        self._save_templates(kept)
        return True

    @staticmethod
    def copy_build(
        source: PlayerBuild,
        *,
        destination_name: str,
        destination_gamertag: str,
        destination_class: str,
        destination_race: str = "",
        destination_role: str = "",
        new_build_name: str = "",
        include_variants: bool = True,
        include_notes: bool = True,
    ) -> BuildReuseResult:
        source_class = source.EsoClass.strip().casefold()
        target_class = str(destination_class or "").strip().casefold()
        if source_class and target_class and source_class != target_class:
            raise ValueError("Exact Build Copy requires the destination character to use the same class. Use a Template for cross-class reuse.")
        payload = BuildReuseService._clean_payload(source, include_variants=include_variants, include_notes=include_notes)
        payload.update(
            {
                "Name": str(destination_name or "").strip(),
                "Gamertag": str(destination_gamertag or "").strip(),
                "EsoClass": str(destination_class or "").strip(),
                "Race": str(destination_race or "").strip(),
                "Role": str(destination_role or source.Role or "").strip(),
                "BuildName": str(new_build_name or source.BuildName or "Copied Build").strip(),
                "ReadyForRaid": False,
            }
        )
        return BuildReuseResult(PlayerBuild.from_dict(payload))

    @classmethod
    def apply_template(
        cls,
        template: BuildTemplateRecord,
        *,
        destination_name: str,
        destination_gamertag: str,
        destination_class: str,
        destination_race: str = "",
        destination_role: str = "",
        new_build_name: str = "",
        include_variants: bool = True,
    ) -> BuildReuseResult:
        payload = deepcopy(template.base_payload)
        class_name = str(destination_class or "").strip()
        overlay = next(
            (value for key, value in template.class_overlays.items() if key.casefold() == class_name.casefold()),
            None,
        )
        warnings: list[str] = []
        if overlay:
            payload = cls._apply_overlay(payload, overlay)
        elif template.class_overlays:
            # Shared role-level skills promoted from multiple overlays remain safe.
            # Class-specific slots stay blank instead of borrowing another class.
            payload["FrontBarSkills"] = cls._normalized_bar(payload.get("FrontBarSkills"))
            payload["BackBarSkills"] = cls._normalized_bar(payload.get("BackBarSkills"))
            payload["ClassSkillLines"] = []
            payload["ClassMasteryAbilityIds"] = []
            payload["ScribedSkills"] = []
            payload["ScribedSkillRecipes"] = []
            warnings.append(
                f"No {class_name or 'destination-class'} overlay exists yet; shared role skills/setup were copied and class-specific slots need review."
            )
        if not include_variants:
            payload["ContextVariants"] = []
            payload["BossLoadouts"] = []
        payload.update(
            {
                "Name": str(destination_name or "").strip(),
                "Gamertag": str(destination_gamertag or "").strip(),
                "EsoClass": class_name,
                "Race": str(destination_race or "").strip(),
                "Role": str(destination_role or template.role or "").strip(),
                "BuildName": str(new_build_name or template.name).strip(),
                "ReadyForRaid": False,
            }
        )
        return BuildReuseResult(PlayerBuild.from_dict(payload), tuple(warnings))

    @staticmethod
    def replace_or_append(roster: BuildRoster, build: PlayerBuild) -> BuildRoster:
        members = list(roster.Members)
        key = (build.Gamertag.strip().casefold(), build.Name.strip().casefold(), build.BuildName.strip().casefold())
        for index, existing in enumerate(members):
            existing_key = (
                existing.Gamertag.strip().casefold(),
                existing.Name.strip().casefold(),
                existing.BuildName.strip().casefold(),
            )
            if existing_key == key:
                members[index] = build
                return BuildRoster(Members=members)
        members.append(build)
        return BuildRoster(Members=members)


__all__ = ["BuildTemplateRecord", "BuildReuseResult", "BuildReuseService"]
