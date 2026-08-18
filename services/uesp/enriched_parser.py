from __future__ import annotations

import re
from dataclasses import replace

from models.uesp_models import UespBoss, UespDialogueLine, UespHealth, UespMechanic, UespPhase
from services.uesp.uesp_parser import (
    UespParser,
    parse_page_html,
    _section,
    ABILITIES_HEADINGS,
    STRATEGY_HEADINGS,
    DIALOGUE_HEADINGS,
    _DIALOGUE_LINE,
)
from services.uesp.mechanic_classifier import classify_mechanic
from services.uesp.phase_extractor import extract_phases


class EnrichedUespParser(UespParser):
    """Validate expanded encounter extraction without replacing UespParser."""

    @staticmethod
    def _health_from_page(parsed) -> UespHealth:
        for block in parsed.all_blocks:
            if block.get("type") != "tr":
                continue
            cells = block.get("cells", [])
            if len(cells) < 2:
                continue
            if cells[0].get("text", "").strip().lower() != "health":
                continue
            text = cells[1].get("text", "")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            numeric = [line for line in lines if re.search(r"\d", line)]
            health = UespHealth()
            if numeric:
                health.normal = re.search(r"[\d,]+", numeric[0]).group(0)
            if len(numeric) >= 2:
                health.veteran = re.search(r"[\d,]+", numeric[1]).group(0)
            if len(numeric) >= 3:
                health.hardmode = numeric[2]
            return health
        return UespHealth()

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
    def _inferred_mechanics(boss: UespBoss) -> list[UespMechanic]:
        result: list[UespMechanic] = []
        for ability in boss.abilities:
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
        boss = super().parse_boss(page, content_id=content_id, content_name=content_name)
        parsed = parse_page_html(page.html)

        strategy_blocks = _section(parsed.sections, STRATEGY_HEADINGS) or []
        ability_blocks = _section(parsed.sections, ABILITIES_HEADINGS) or []
        phase_facts = extract_phases(strategy_blocks + ability_blocks)
        phases = [UespPhase(fact.label, fact.threshold, fact.description) for fact in phase_facts]

        dialogue_blocks = _section(parsed.sections, DIALOGUE_HEADINGS) or []
        dialogue = self._dialogue_from_blocks(dialogue_blocks)
        grouped: dict[str, list[UespDialogueLine]] = {}
        for line in dialogue:
            grouped.setdefault(line.trigger or "Unspecified", []).append(line)

        mechanics = list(boss.mechanics)
        existing = {(mechanic.name, mechanic.description) for mechanic in mechanics}
        for mechanic in self._inferred_mechanics(boss):
            if (mechanic.name, mechanic.description) not in existing:
                mechanics.append(mechanic)

        return replace(
            boss,
            health=self._health_from_page(parsed),
            phases=phases,
            dialogue=dialogue,
            dialogue_by_trigger=grouped,
            mechanics=mechanics,
        )
