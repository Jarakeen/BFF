# services/uesp/uesp_parser.py
"""
Turns a UespPage (rendered HTML from UESP's own action=parse API)
into the structured dataclasses in models/uesp_models.py.

Design note: this parses UESP's rendered HTML rather than raw wikitext.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
import urllib
from datetime import datetime, timezone

from models.uesp_models import (
    UespAbility,
    UespAchievement,
    UespBoss,
    UespContent,
    UespDialogueLine,
    UespDifficultyNotes,
    UespHealth,
    UespMechanic,
    UespPhase,
    UespSource,
)
from services.uesp.uesp_client import UespPage

_HEALTH_NORMAL_MARKER = "\x00HEALTH_NORMAL\x00"
_HEALTH_VETERAN_MARKER = "\x00HEALTH_VETERAN\x00"
ABILITIES_HEADINGS = {"skills and abilities", "abilities", "skills"}
STRATEGY_HEADINGS = {"strategy", "strategies", "tactics"}
NOTES_HEADINGS = {"notes", "trivia"}
QUEST_HEADINGS = {"related quests", "quests"}
DIALOGUE_HEADINGS = {"quest-related events", "dialogue", "conversation", "conversations"}
ACHIEVEMENT_HEADINGS = {"achievements", "related achievements"}
BOSS_SECTION_HEADINGS = {"bosses", "boss and encounters", "bosses and encounters", "encounters"}
NPC_HEADINGS = {"related npcs", "npcs", "notable npcs"}
_NON_CONTENT_TITLE_PREFIXES = ("File:", "Category:", "Special:", "Help:", "Template:", "User:")
MECHANICS_HEADINGS = {"mechanics", "mechanic"}
_BLOCK_TAGS = {"h2", "h3", "h4", "p", "li", "dt", "dd", "th", "td"}
_SKIP_ID_PREFIXES = ("toc",)
_SKIP_CLASS_MARKERS = ("navbox", "toccolours", "metadata", "noprint", "mw-editsection", "reflist")
_BR_TOKEN = "\x00BR\x00"


def _finalize_text(buffer: list[str]) -> str:
    raw = "".join(buffer)
    collapsed = re.sub(r"\s+", " ", raw).strip()
    collapsed = re.sub(rf"\s*{re.escape(_BR_TOKEN)}\s*", "\n", collapsed)
    return collapsed.strip()


class _PageHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self._buffer_stack: list[list[str]] = []
        self._links_stack: list[list[tuple[str, str]]] = []
        self._row_stack: list[list[dict]] = []
        self._anchor_stack: list[tuple[str, int]] = []
        self._skip_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: (value or "") for key, value in attrs}
        if self._skip_stack:
            if self._should_skip(tag, attrs_dict):
                self._skip_stack.append(tag)
            return
        if self._should_skip(tag, attrs_dict):
            self._skip_stack.append(tag)
            return
        if tag == "br":
            if self._buffer_stack:
                self._buffer_stack[-1].append(_BR_TOKEN)
            return
        if tag == "a":
            start_index = len(self._buffer_stack[-1]) if self._buffer_stack else 0
            self._anchor_stack.append((attrs_dict.get("href", ""), start_index))
            return
        if tag == "tr":
            self._row_stack.append([])
            return
        if tag in ("th", "td"):
            self._buffer_stack.append([])
            self._links_stack.append([])
            return
        if tag in _BLOCK_TAGS:
            self._buffer_stack.append([])
            self._links_stack.append([])

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br" and self._buffer_stack and not self._skip_stack:
            self._buffer_stack[-1].append(_BR_TOKEN)

    def handle_endtag(self, tag: str) -> None:
        if self._skip_stack:
            if tag == self._skip_stack[-1]:
                self._skip_stack.pop()
            return
        if tag == "a":
            if self._anchor_stack:
                href, start_index = self._anchor_stack.pop()
                if self._buffer_stack and href:
                    anchor_text = re.sub(r"\s+", " ", "".join(self._buffer_stack[-1][start_index:])).strip()
                    if self._links_stack:
                        self._links_stack[-1].append((href, anchor_text))
                    if href.endswith("ON-icon-Normal.png"):
                        self._buffer_stack[-1].append(_HEALTH_NORMAL_MARKER)
                    elif "/Online:Veteran" in href:
                        self._buffer_stack[-1].append(_HEALTH_VETERAN_MARKER)
            return
        if tag == "tr":
            if self._row_stack:
                self.blocks.append({"type": "tr", "cells": self._row_stack.pop()})
            return
        if tag not in _BLOCK_TAGS or not self._buffer_stack:
            return
        text = _finalize_text(self._buffer_stack.pop())
        links = self._links_stack.pop() if self._links_stack else []
        if tag in ("th", "td"):
            cell = {"text": text, "links": links}
            if self._row_stack:
                self._row_stack[-1].append(cell)
            else:
                self.blocks.append({"type": tag, **cell})
        elif tag[0] == "h" and tag[1:].isdigit():
            self.blocks.append({"type": "heading", "level": int(tag[1:]), "text": text})
        elif text:
            self.blocks.append({"type": tag, "text": text, "links": links})

    def handle_data(self, data: str) -> None:
        if not self._skip_stack and self._buffer_stack:
            self._buffer_stack[-1].append(data)

    @staticmethod
    def _should_skip(tag: str, attrs_dict: dict[str, str]) -> bool:
        if tag not in ("div", "table", "span", "sup", "ul"):
            return False
        element_id = attrs_dict.get("id", "").lower()
        classes = attrs_dict.get("class", "").lower()
        return any(element_id.startswith(prefix) for prefix in _SKIP_ID_PREFIXES) or any(marker in classes for marker in _SKIP_CLASS_MARKERS)


@dataclass
class _ParsedPage:
    summary: str
    infobox: dict[str, str]
    sections: dict[str, list[dict]]
    all_blocks: list[dict]


def parse_page_html(html: str) -> _ParsedPage:
    parser = _PageHtmlParser()
    parser.feed(html)
    blocks = parser.blocks
    preamble: list[dict] = []
    sections: dict[str, list[dict]] = {}
    current_heading: str | None = None
    for block in blocks:
        if block["type"] == "heading":
            current_heading = block["text"].strip()
            sections.setdefault(current_heading, [])
        elif current_heading is None:
            preamble.append(block)
        else:
            sections[current_heading].append(block)
    infobox: dict[str, str] = {}
    summary_paragraphs: list[str] = []
    for block in preamble:
        if block["type"] == "tr":
            cells = block.get("cells", [])
            if len(cells) < 2:
                continue
            label = cells[0].get("text", "").strip().lower()
            if label:
                value = cells[1].get("text", "").strip()
                if value:
                    infobox[label] = value
        elif block["type"] == "p" and block["text"].strip():
            summary_paragraphs.append(block["text"].strip())
    return _ParsedPage(" ".join(summary_paragraphs), infobox, sections, blocks)


def _section(sections: dict[str, list[dict]], aliases: set[str]) -> list[dict] | None:
    for heading, blocks in sections.items():
        if heading.lower().strip() in aliases:
            return blocks
    return None


def _extract_health(cell: dict) -> UespHealth:
    text = cell.get("text", "")
    health = UespHealth()
    normal_parts = text.split(_HEALTH_NORMAL_MARKER)
    if len(normal_parts) < 2:
        return health
    veteran_parts = normal_parts[1].split(_HEALTH_VETERAN_MARKER)
    if veteran_parts:
        match = re.search(r"([\d,]+)", veteran_parts[0])
        if match:
            health.normal = match.group(1)
    if len(veteran_parts) >= 2:
        match = re.search(r"([\d,]+)", veteran_parts[1])
        if match:
            health.veteran = match.group(1)
    if len(veteran_parts) >= 3:
        match = re.search(r"([\d,]+)", veteran_parts[2])
        if match:
            health.hardmode = match.group(1)
    return health


def _extract_abilities(blocks: list[dict]) -> list[UespAbility]:
    abilities: list[UespAbility] = []
    pending_name: str | None = None
    for block in blocks:
        if block["type"] == "dt":
            pending_name = block["text"].strip()
        elif block["type"] == "dd" and pending_name:
            abilities.append(UespAbility(name=pending_name, description=block["text"].strip()))
            pending_name = None
    return abilities


def _extract_mechanics(blocks: list[dict]) -> list[UespMechanic]:
    mechanics: list[UespMechanic] = []
    for block in blocks:
        if block["type"] != "p":
            continue
        text = block.get("text", "").strip()
        if not text:
            continue
        links = [title for _, title in block.get("links", []) if title]
        name = links[0] if links else "Unnamed mechanic"
        mechanics.append(UespMechanic(name=name, description=text, links=links))
    return mechanics


_PHASE_HEALTH_PATTERN = re.compile(r"(?i)\b(?:at|reaches?|below|under)\s+(\d{1,3})\s*%\s*(?:health)?")


def _extract_phases(blocks: list[dict]) -> list[UespPhase]:
    phases: list[UespPhase] = []
    seen: set[tuple[str, str]] = set()
    pending_phase_name: str | None = None
    for block in blocks:
        block_type = block.get("type", "")
        text = block.get("text", "").strip()
        if not text:
            continue
        if block_type == "dt":
            pending_phase_name = text if "phase" in text.lower() else None
            continue
        if block_type != "dd" or not pending_phase_name:
            continue
        match = _PHASE_HEALTH_PATTERN.search(text)
        if not match:
            continue
        threshold = f"{match.group(1)}%"
        key = (pending_phase_name, threshold)
        if key in seen:
            continue
        seen.add(key)
        phases.append(UespPhase(label=pending_phase_name, threshold=threshold, description=text))
        pending_phase_name = None
    return phases


def _extract_dialogue(blocks: list[dict]) -> list[UespDialogueLine]:
    dialogue: list[UespDialogueLine] = []
    current_trigger = ""
    for block in blocks:
        block_type = block.get("type", "")
        text = block.get("text", "").strip()
        if not text:
            continue
        if block_type == "p":
            current_trigger = text.rstrip(":").strip()
            continue
        if block_type != "dd":
            continue
        speaker = ""
        line = text
        if ":" in text:
            possible_speaker, possible_line = text.split(":", 1)
            if possible_speaker.strip() and possible_line.strip():
                speaker = possible_speaker.strip()
                line = possible_line.strip()
        if len(line) >= 2 and line.startswith('"') and line.endswith('"'):
            line = line[1:-1].strip()
        dialogue.append(UespDialogueLine(speaker=speaker, line=line, trigger=current_trigger))
    return dialogue


def _group_dialogue_by_trigger(dialogue: list[UespDialogueLine]) -> dict[str, list[UespDialogueLine]]:
    grouped: dict[str, list[UespDialogueLine]] = {}
    for entry in dialogue:
        trigger = entry.trigger.strip() or "Unspecified"
        grouped.setdefault(trigger, []).append(entry)
    return grouped


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _match_dialogue_trigger_to_ability(trigger: str, dialogue: list[UespDialogueLine], abilities: list[UespAbility]) -> str | None:
    normalized_trigger = _normalize_text(trigger)
    trigger_words = set(normalized_trigger.split()) - {"attack", "ability", "phase", "event"}
    if not trigger_words or normalized_trigger in {"idling before combat", "group wipe"}:
        return None
    best_match: str | None = None
    best_score = 0
    for ability in abilities:
        name_words = set(_normalize_text(ability.name).split())
        description_words = set(_normalize_text(ability.description).split())
        score = len(trigger_words & name_words) * 10 + len(trigger_words & description_words) * 5
        for entry in dialogue:
            if entry.trigger.strip() == trigger.strip():
                score += len(set(_normalize_text(entry.line).split()) & description_words)
        if score > best_score:
            best_score = score
            best_match = ability.name
    return best_match if best_score >= 5 else None


def _extract_list_text(blocks: list[dict]) -> list[str]:
    items = [b["text"].strip() for b in blocks if b["type"] == "li" and b["text"].strip()]
    return items or [b["text"].strip() for b in blocks if b["type"] == "p" and b["text"].strip()]


def _title_from_href(href: str) -> str | None:
    if not href:
        return None
    match = re.match(r"^/wiki/([^#?]+)", href)
    if not match:
        return None
    return urllib.parse.unquote(match.group(1)).replace("_", " ")


def _looks_like_content_title(title: str) -> bool:
    return not any(title.startswith(prefix) for prefix in _NON_CONTENT_TITLE_PREFIXES)


def _extract_linked_titles(blocks: list[dict]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for block in blocks:
        for href, text in block.get("links", []):
            title = _title_from_href(href)
            if not title or not _looks_like_content_title(title) or title in seen:
                continue
            seen.add(title)
            refs.append((text.strip() or title, title))
    return refs


def _extract_difficulty_notes(paragraphs: list[str]) -> UespDifficultyNotes:
    notes = UespDifficultyNotes()
    for paragraph in paragraphs:
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            lowered = sentence.lower()
            if "hard mode" in lowered:
                notes.hardmode_info.append(sentence)
            elif "veteran" in lowered and ("normal" in lowered or "difference" in lowered):
                notes.normal_veteran_differences.append(sentence)
    return notes


def slugify(title: str) -> str:
    text = title.split(":", 1)[-1] if ":" in title else title
    text = re.sub(r"[^A-Za-z0-9]+", "_", text.strip())
    return text.strip("_").lower()


def _clean_title(title: str) -> str:
    return title.split(":", 1)[-1].strip() if ":" in title else title.strip()


def _page_url(title: str) -> str:
    return f"https://en.uesp.net/wiki/{urllib.parse.quote(title.replace(' ', '_'), safe=':()')}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source_for(page: UespPage) -> UespSource:
    return UespSource(url=_page_url(page.title), page_title=page.title, revision_id=page.revision_id, retrieved_at=_now_iso())


class UespParser:
    def parse_boss(self, page: UespPage, content_id: str = "", content_name: str = "") -> UespBoss:
        parsed = parse_page_html(page.html)
        infobox = parsed.infobox
        abilities_blocks = _section(parsed.sections, ABILITIES_HEADINGS) or []
        abilities = _extract_abilities(abilities_blocks)
        mechanics_blocks = _section(parsed.sections, MECHANICS_HEADINGS) or []
        mechanics = _extract_mechanics(mechanics_blocks)
        strategy_blocks = _section(parsed.sections, STRATEGY_HEADINGS) or []
        strategy_paragraphs = [b["text"] for b in strategy_blocks if b["type"] == "p" and b["text"].strip()]
        phases = _extract_phases(abilities_blocks)
        dialogue_blocks = _section(parsed.sections, DIALOGUE_HEADINGS) or []
        dialogue = _extract_dialogue(dialogue_blocks)
        dialogue_by_trigger = _group_dialogue_by_trigger(dialogue)
        for trigger, entries in dialogue_by_trigger.items():
            matched_ability = _match_dialogue_trigger_to_ability(trigger, entries, abilities)
            for entry in entries:
                entry.ability = matched_ability
        notes = _extract_list_text(_section(parsed.sections, NOTES_HEADINGS) or [])
        related_quests = _extract_list_text(_section(parsed.sections, QUEST_HEADINGS) or [])
        related_npcs = _extract_list_text(_section(parsed.sections, NPC_HEADINGS) or [])
        all_paragraphs = [b["text"] for b in parsed.all_blocks if b["type"] == "p" and b["text"].strip()]
        difficulty_notes = _extract_difficulty_notes(all_paragraphs)
        achievement_refs = _extract_linked_titles(_section(parsed.sections, ACHIEVEMENT_HEADINGS) or [])
        health_block = next((block for block in parsed.all_blocks if block.get("type") == "tr" and block.get("cells") and block["cells"][0].get("text", "").strip().lower() == "health" and len(block["cells"]) >= 2), {"cells": [{}, {"text": ""}]})
        return UespBoss(
            id=slugify(page.title), name=_clean_title(page.title), content_id=content_id, content_name=content_name,
            location=infobox.get("location", ""), species=infobox.get("species", ""), reaction=infobox.get("reaction", ""),
            health=_extract_health(health_block["cells"][1]), abilities=abilities, mechanics=mechanics, phases=phases,
            dialogue=dialogue, dialogue_by_trigger=dialogue_by_trigger, difficulty_notes=difficulty_notes,
            strategy_notes=strategy_paragraphs, notes=notes, related_npcs=related_npcs, related_quests=related_quests,
            achievements=[UespAchievement(id=slugify(title), name=display_text) for display_text, title in achievement_refs],
            summary=parsed.summary, source=_source_for(page),
        )

    def parse_content(self, page: UespPage, content_type: str) -> UespContent:
        parsed = parse_page_html(page.html)
        achievement_refs = _extract_linked_titles(_section(parsed.sections, ACHIEVEMENT_HEADINGS) or [])
        notes = _extract_list_text(_section(parsed.sections, NOTES_HEADINGS) or [])
        related_npcs = _extract_list_text(_section(parsed.sections, NPC_HEADINGS) or [])
        return UespContent(id=slugify(page.title), name=_clean_title(page.title), content_type=content_type, summary=parsed.summary,
            location=parsed.infobox.get("location", ""), achievements=[UespAchievement(id=slugify(title), name=display_text) for display_text, title in achievement_refs],
            related_npcs=related_npcs, notes=notes, source=_source_for(page))

    def parse_achievement(self, page: UespPage) -> UespAchievement:
        parsed = parse_page_html(page.html)
        return UespAchievement(id=slugify(page.title), name=_clean_title(page.title), description=parsed.summary, source=_source_for(page))

    @staticmethod
    def _dedupe_titles(titles: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for title in titles:
            normalized = title.strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(normalized)
        return result

    def find_boss_links(self, page: UespPage) -> list[str]:
        parsed = parse_page_html(page.html)
        blocks = _section(parsed.sections, BOSS_SECTION_HEADINGS)
        if not blocks:
            return []
        candidates = [title for _, title in _extract_linked_titles(blocks) if title.strip()]
        excluded_words = ("achievement", "achievements", "quest", "quests", "item", "set", "style", "furnishing", "collectible", "monster", "npc", "location", "zone", "guide", "strategy", "journal")
        generic_pages = {"arenas", "dungeons", "trials", "murkmire", "dead water village", "imperial", "blackguards"}
        filtered: list[str] = []
        for title in candidates:
            lowered = title.casefold()
            if lowered in generic_pages or any(word in lowered for word in excluded_words):
                continue
            filtered.append(title)
        return self._dedupe_titles(filtered)

    def detect_content_type(self, page: UespPage, default: str) -> str:
        categories_lower = {category.lower() for category in page.categories}
        if any("dungeon" in category for category in categories_lower):
            return "dungeon"
        if any("arena" in category for category in categories_lower):
            return "arena"
        if any("trial" in category for category in categories_lower):
            return "trial"
        return default
