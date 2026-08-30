from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class ScribedSkillRecipe:
    """One configured ESO scribed skill.

    ResultName remains explicit because the current canonical data stack does
    not yet contain a verified name mapping for every Grimoire + Focus pair.
    """

    ResultName: str = ""
    Grimoire: str = ""
    Focus: str = ""
    Signature: str = ""
    Affix: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "ScribedSkillRecipe":
        data = dict(data or {})
        return cls(
            ResultName=str(data.get("ResultName", data.get("Name", "")) or "").strip(),
            Grimoire=str(data.get("Grimoire", "") or "").strip(),
            Focus=str(data.get("Focus", "") or "").strip(),
            Signature=str(data.get("Signature", "") or "").strip(),
            Affix=str(data.get("Affix", "") or "").strip(),
        )

    @classmethod
    def from_legacy_name(cls, name: str) -> "ScribedSkillRecipe":
        return cls(ResultName=str(name or "").strip())

    @property
    def is_complete(self) -> bool:
        return bool(self.ResultName and self.Grimoire and self.Focus and self.Signature and self.Affix)

    @property
    def recipe_text(self) -> str:
        parts = [self.Grimoire, self.Focus, self.Signature, self.Affix]
        return " • ".join(part for part in parts if part)
