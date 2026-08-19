from __future__ import annotations

import re
from dataclasses import replace

from models.uesp_models import UespAchievement, UespBoss, UespDialogueLine, UespHealth, UespMechanic, UespPhase
from services.uesp.uesp_parser import (
    UespParser,
    parse_page_html,
    _section,
    ABILITIES_HEADINGS,
    STRATEGY_HEADINGS,
    DIALOGUE_HEADINGS,
    ACHIEVEMENT_HEADINGS,
    NOTES_HEADINGS,
    QUEST_HEADINGS,
    NPC_HEADINGS,
    MECHANICS_HEADINGS,
    _DIALOGUE_LINE,
    _extract_abilities,
    _extract_mechanics,
    _extract_list_text,
    _extract_linked_titles,
    _extract_difficulty_notes,
    _source_for,
    _clean_title,
    slugify,
)
from services.uesp.mechanic_classifier import classify_mechanic
from services.uesp.phase_extractor import extract_phases


class EnrichedUespParser(UespParser):
    """Expanded boss extraction without replacing the existing parser yet."""

    def _health_from_page(self, parsed) -> UespHealth:
        return UespParser._health_from_page(self, parsed)

    @staticmethod
    def _dialogue_from_blocks(blocks: list[dict]) -> list[UespDialogueLine]:
        result: list[UespDialogueLine] = []
        trigger = ""
        for block in blocks:
            kind = block.get("type", "")
            text = block.get("text", "").strip()
            if not text:
                continue
            if kind == "p":
                trigger = text
                continue
            if kind not in {"li", "dd"}:
                continue
            match = _DIALOGUE_LINE.match(text)
            if match:
                speaker, line = match.group(1).strip(), match.group(2).strip()
            else:
                speaker, line = "", text
            result.append(UespDialogueLine(speaker=speaker, line=line, trigger=trigger))
        return result

    @staticmethod
    def _inferred_mechanics(abilities) -> list[UespMechanic]:
        result: list[UespMechanic] = []
        for ability in abilities:
            classification = classify_mechanic(ability.name, ability.description)
            if classification.mechanic_type is None:
                continue
            result.append(
                UespMechanic(
                    name=ability.name,
                    description=ability.description,
                    mechanic_type=classification.mechanic_type,
                    damage_type=classification.damage_type,
                    target_count=classification.target_count,
                    requires_movement=classification.requires_movement,
                    requires_positioning=classification.requires_positioning,
                    requires_cleanse=classification.requires_cleanse,
                    persistent_hazard=classification.persistent_hazard,
                    failure_is_fatal=classification.failure_is_fatal,
                    interruptible=classification.interruptible,
                    interrupt_note=classification.interrupt_note,
                    interpretation_status="inferred",
                )
            )
        return result

    def parse_boss(self, page, content_id: str = "", content_name: str = "") -> UespBoss:
        parsed = parse_page_html(page.html)
        infobox = parsed.infobox

        abilities_blocks = _section(parsed.sections, ABILITIES_HEADINGS) or []
        abilities = _extract_abilities(abilities_blocks)

        mechanics_blocks = _section(parsed.sections, MECHANICS_HEADINGS) or []
        mechanics = _extract_mechanics(mechanics_blocks)

        strategy_blocks = _section(parsed.sections, STRATEGY_HEADINGS) or []
        strategy_notes = [
            block["text"] for block in strategy_blocks
            if block.get("type") == "p" and block.get("text", "").strip()
        ]

        phase_facts = extract_phases(strategy_blocks + abilities_blocks)
        phases = [UespPhase(fact.label, fact.threshold, fact.description) for fact in phase_facts]

        dialogue_blocks = _section(parsed.sections, DIALOGUE_HEADINGS) or []
        dialogue = self._dialogue_from_blocks(dialogue_blocks)
        grouped: dict[str, list[UespDialogueLine]] = {}
        for line in dialogue:
            grouped.setdefault(line.trigger or "Unspecified", []).append(line)

        existing = {(mechanic.name, mechanic.description) for mechanic in mechanics}
        for mechanic in self._inferred_mechanics(abilities):
            if (mechanic.name, mechanic.description) not in existing:
                mechanics.append(mechanic)

        notes = _extract_list_text(_section(parsed.sections, NOTES_HEADINGS) or [])
        related_quests = _extract_list_text(_section(parsed.sections, QUEST_HEADINGS) or [])
        related_npcs = _extract_list_text(_section(parsed.sections, NPC_HEADINGS) or [])

        difficulty_text = [
            block["text"]
            for block in (
                strategy_blocks
                + (_section(parsed.sections, NOTES_HEADINGS) or [])
            )
            if block.get("type") in {"p", "li"}
            and block.get("text", "").strip()
        ]

        difficulty_notes = _extract_difficulty_notes(difficulty_text)


        achievement_refs = _extract_linked_titles(
            _section(parsed.sections, ACHIEVEMENT_HEADINGS) or []
)
        return UespBoss(
            id=slugify(page.title),
            name=_clean_title(page.title),
            content_id=content_id,
            content_name=content_name,
            location=infobox.get("location", ""),
            species=infobox.get("species", ""),
            reaction=infobox.get("reaction", ""),
            health=self._health_from_page(parsed),
            abilities=abilities,
            mechanics=mechanics,
            phases=phases,
            dialogue=dialogue,
            dialogue_by_trigger=grouped,
            difficulty_notes=difficulty_notes,
            strategy_notes=strategy_notes,
            notes=notes,
            related_npcs=related_npcs,
            related_quests=related_quests,
            achievements=[
                UespAchievement(id=slugify(title), name=display_text)
                for display_text, title in achievement_refs
            ],
            summary=parsed.summary,
            source=_source_for(page),
        )
