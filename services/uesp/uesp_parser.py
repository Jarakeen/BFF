# services/uesp/uesp_parser.py
"""
Turns a UespPage (rendered HTML from UESP's own action=parse API)
into the structured dataclasses in models/uesp_models.py.

Design note: this parses UESP's *rendered HTML* rather than raw
wikitext. Raw wikitext depends on template internals (parameter
names inside {{Online Boss Summary|...}}) that aren't documented and
can change per page; the rendered HTML UESP's own API produces
(headings, tables, definition lists) is the stable, structural
contract every page shares. Nothing here invents information - every
field is either lifted verbatim from a block of extracted text or
left empty/absent when the source page doesn't have it.

Known limitation: the HTML "skip" logic for navboxes/TOC blocks is a
simple matching-tag heuristic, not a full DOM tree. On pages with
unusual nested markup this can occasionally leave a stray nav/TOC
line in a section's block list; it will never fabricate content that
isn't literally in the page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
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


# --------------------------------------------------
# Heading aliases (case-insensitive match against <h2>/<h3> text)
# --------------------------------------------------
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
MECHANICS_HEADINGS = {
    "mechanics",
    "mechanic",
}

# --------------------------------------------------
# HTML -> flat block list
# --------------------------------------------------

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
    """Flattens UESP's rendered article HTML into an ordered list of
    blocks (headings, paragraphs, list items, definition terms, table
    rows), each tagged with any links found inside it.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)

        self.blocks: list[dict] = []

        self._buffer_stack: list[list[str]] = []
        self._links_stack: list[list[tuple[str, str]]] = []
        self._row_stack: list[list[dict]] = []
        self._anchor_stack: list[tuple[str, int]] = []
        self._skip_stack: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
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
            href = attrs_dict.get("href", "")

            start_index = (
                len(self._buffer_stack[-1])
                if self._buffer_stack
                else 0
            )

            self._anchor_stack.append(
                (href, start_index)
            )

            return

        # Start a new table row.
        if tag == "tr":
            self._row_stack.append([])
            return

        # Every table cell gets its own text buffer.
        if tag in ("th", "td"):
            self._buffer_stack.append([])
            self._links_stack.append([])
            return

        if tag in _BLOCK_TAGS:
            self._buffer_stack.append([])
            self._links_stack.append([])

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
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
                    anchor_text = "".join(
                        self._buffer_stack[-1][start_index:]
                    )

                    anchor_text = re.sub(
                        r"\s+",
                        " ",
                        anchor_text,
                    ).strip()

                    if self._links_stack:
                        self._links_stack[-1].append(
                            (href, anchor_text)
                        )

                    # UESP health values are separated by difficulty icons.
                    # The icons contain no text, so preserve their position
                    # in the buffer for _extract_health().
                    if href.endswith("ON-icon-Normal.png"):
                        self._buffer_stack[-1].append(
                            _HEALTH_NORMAL_MARKER
                        )
                    elif "/Online:Veteran" in href:
                        self._buffer_stack[-1].append(
                            _HEALTH_VETERAN_MARKER
                        )

            return

        if tag == "tr":
            if self._row_stack:
                cells = self._row_stack.pop()

                self.blocks.append(
                    {
                        "type": "tr",
                        "cells": cells,
                    }
                )
            return

        if tag not in _BLOCK_TAGS:
            return

        if not self._buffer_stack:
            return

        text = _finalize_text(
            self._buffer_stack.pop()
        )

        links = (
            self._links_stack.pop()
            if self._links_stack
            else []
        )

        if tag in ("th", "td"):
            cell = {
                "text": text,
                "links": links,
            }

            # UESP health cells use icon links to separate
            # Normal / Veteran / Hardmode values. Preserve the
            # link information so health extraction can distinguish
            # the values later.

            if self._row_stack:
                self._row_stack[-1].append(cell)
            else:
                self.blocks.append(
                    {
                        "type": tag,
                        **cell,
                    }
                )

        elif tag[0] == "h" and tag[1:].isdigit():
            self.blocks.append(
                {
                    "type": "heading",
                    "level": int(tag[1:]),
                    "text": text,
                }
            )

        else:
            if text:
                self.blocks.append(
                    {
                        "type": tag,
                        "text": text,
                        "links": links,
                    }
                )

    def handle_data(self, data: str) -> None:
        if self._skip_stack:
            return

        if self._buffer_stack:
            self._buffer_stack[-1].append(data)

    @staticmethod
    def _should_skip(
        tag: str,
        attrs_dict: dict[str, str],
    ) -> bool:

        if tag not in (
            "div",
            "table",
            "span",
            "sup",
            "ul",
        ):
            return False

        element_id = attrs_dict.get(
            "id",
            "",
        ).lower()

        classes = attrs_dict.get(
            "class",
            "",
        ).lower()

        if any(
            element_id.startswith(prefix)
            for prefix in _SKIP_ID_PREFIXES
        ):
            return True

        if any(
            marker in classes
            for marker in _SKIP_CLASS_MARKERS
        ):
            return True

        return False


@dataclass
class _ParsedPage:
    summary: str
    infobox: dict[str, str]
    sections: dict[str, list[dict]]
    all_blocks: list[dict]


def parse_page_html(html: str) -> _ParsedPage:
    """Split a page's rendered HTML into an infobox dict, a lead
    summary, and named sections keyed by heading text."""

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
            continue

        if current_heading is None:
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

            if not label:
                continue

            value_parts: list[str] = []

            for cell in cells[1:2]:
                text = cell.get("text", "").strip()

                if text:
                    value_parts.append(text)

            value = " ".join(value_parts).strip()

            if value:
                infobox[label] = value

        elif block["type"] == "p" and block["text"].strip():
            summary_paragraphs.append(block["text"].strip())

    return _ParsedPage(
        summary=" ".join(summary_paragraphs),
        infobox=infobox,
        sections=sections,
        all_blocks=blocks,
    )

def _section(sections: dict[str, list[dict]], aliases: set[str]) -> list[dict] | None:
    for heading, blocks in sections.items():
        if heading.lower().strip() in aliases:
            return blocks
    return None


# --------------------------------------------------
# Field extraction helpers
# --------------------------------------------------

_DIALOGUE_LINE = re.compile(r'^([A-Z][\w\s\-\'.]{0,60}?):\s*"(.+)"\s*$')
_PHASE_PATTERN = re.compile(r"(?i)phase\s+(\d+)[^.]{0,200}?(\d{1,3})\s?%")


def _extract_health(cell: dict) -> UespHealth:
    text = cell.get("text", "")

    health = UespHealth()

    normal_parts = text.split(_HEALTH_NORMAL_MARKER)
    if len(normal_parts) < 2:
        return health

    after_normal = normal_parts[1]

    veteran_parts = after_normal.split(_HEALTH_VETERAN_MARKER)

    if len(veteran_parts) >= 1:
        normal_match = re.search(
            r"([\d,]+)",
            veteran_parts[0],
        )

        if normal_match:
            health.normal = normal_match.group(1)

    if len(veteran_parts) >= 2:
        veteran_match = re.search(
            r"([\d,]+)",
            veteran_parts[1],
        )

        if veteran_match:
            health.veteran = veteran_match.group(1)

    if len(veteran_parts) >= 3:
        hardmode_match = re.search(
            r"([\d,]+)",
            veteran_parts[2],
        )

        if hardmode_match:
            health.hardmode = hardmode_match.group(1)

    return health


def _extract_abilities(blocks: list[dict]) -> list[UespAbility]:
    abilities: list[UespAbility] = []
    pending_name: str | None = None

    for block in blocks:
        if block["type"] == "dt":
            pending_name = block["text"].strip()
        elif block["type"] == "dd" and pending_name:
            abilities.append(
                UespAbility(name=pending_name, description=block["text"].strip())
            )
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

        links = [
            title
            for _, title in block.get("links", [])
            if title
        ]

        mechanics.append(
            UespMechanic(
                description=text,
                links=links,
            )
        )

    return mechanics


_PHASE_HEALTH_PATTERN = re.compile(
    r"(?i)\b(?:at|reaches?|below|under)\s+(\d{1,3})\s*%\s*(?:health)?"
)


def _extract_phases(blocks: list[dict]) -> list[UespPhase]:
    phases: list[UespPhase] = []
    seen: set[tuple[str, str]] = set()

    pending_phase_name: str | None = None

    for block in blocks:
        block_type = block.get("type", "")
        text = block.get("text", "").strip()

        if not text:
            continue

        # A definition-term such as:
        #   Execute Phase
        #
        # followed by a definition-description containing:
        #   One she reaches 10% health...
        if block_type == "dt":
            if "phase" in text.lower():
                pending_phase_name = text
            else:
                pending_phase_name = None

            continue

        if block_type != "dd":
            continue

        if not pending_phase_name:
            continue

        match = _PHASE_HEALTH_PATTERN.search(text)

        if not match:
            continue

        threshold = f"{match.group(1)}%"
        key = (pending_phase_name, threshold)

        if key in seen:
            continue

        seen.add(key)

        phases.append(
            UespPhase(
                label=pending_phase_name,
                threshold=threshold,
                description=text,
            )
        )

        pending_phase_name = None

    return phases


def _extract_dialogue(
    blocks: list[dict],
) -> list[UespDialogueLine]:
    dialogue: list[UespDialogueLine] = []
    current_trigger = ""

    for block in blocks:
        block_type = block.get("type", "")
        text = block.get("text", "").strip()

        if not text:
            continue

        # UESP uses paragraph text as the dialogue trigger/context.
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

        dialogue.append(
            UespDialogueLine(
                speaker=speaker,
                line=line,
                trigger=current_trigger,
            )
        )

    return dialogue


def _group_dialogue_by_trigger(
    dialogue: list[UespDialogueLine],
) -> dict[str, list[UespDialogueLine]]:
    grouped: dict[str, list[UespDialogueLine]] = {}

    for entry in dialogue:
        trigger = entry.trigger.strip() or "Unspecified"
        grouped.setdefault(trigger, []).append(entry)

    return grouped


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _match_dialogue_trigger_to_ability(
    trigger: str,
    dialogue: list[UespDialogueLine],
    abilities: list[UespAbility],
) -> str | None:
    normalized_trigger = _normalize_text(trigger)
    trigger_words = set(normalized_trigger.split())

    trigger_words -= {"attack", "ability", "phase", "event"}

    if not trigger_words:
        return None

    # These are contextual dialogue headings, not ability events.
    if normalized_trigger in {"idling before combat", "group wipe"}:
        return None

    best_match: str | None = None
    best_score = 0

    for ability in abilities:
        name_words = set(_normalize_text(ability.name).split())
        description_words = set(_normalize_text(ability.description).split())

        score = 0

        # Exact conceptual overlap with the ability name is strongest.
        score += len(trigger_words & name_words) * 10

        # Trigger words appearing in the ability description are strong evidence.
        score += len(trigger_words & description_words) * 5

        # Individual dialogue lines provide secondary evidence, but do not
        # pool unrelated lines from different triggers together.
        for entry in dialogue:
            if entry.trigger.strip() != trigger.strip():
                continue
            line_words = set(_normalize_text(entry.line).split())
            score += len(line_words & description_words)

        if score > best_score:
            best_score = score
            best_match = ability.name

    if best_score < 5:
        return None

    return best_match

def _extract_list_text(blocks: list[dict]) -> list[str]:
    items = [b["text"].strip() for b in blocks if b["type"] == "li" and b["text"].strip()]
    if not items:
        items = [b["text"].strip() for b in blocks if b["type"] == "p" and b["text"].strip()]
    return items


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
    """Return (display_text, wiki_title) pairs for every content-page
    link found inside a set of blocks."""

    refs: list[tuple[str, str]] = []
    seen: set[str] = set()

    for block in blocks:
        for href, text in block.get("links", []):
            title = _title_from_href(href)
            if not title or not _looks_like_content_title(title):
                continue
            if title in seen:
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
    """Stable ID from a UESP page title. Keeps disambiguators like
    "(Rockgrove)" rather than stripping them, since page titles are
    already unique on the wiki and stripping could collide two
    same-named bosses from different content."""

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
    return UespSource(
        url=_page_url(page.title),
        page_title=page.title,
        revision_id=page.revision_id,
        retrieved_at=_now_iso(),
    )


# --------------------------------------------------
# Public parser
# --------------------------------------------------

class UespParser:
    """Converts fetched UespPage objects into the structured
    dataclasses that get written to data/uesp/."""

    def parse_boss(
        self,
        page: UespPage,
        content_id: str = "",
        content_name: str = "",
    ) -> UespBoss:

        parsed = parse_page_html(page.html)
        infobox = parsed.infobox

        # --------------------------------------------------
        # Abilities
        # --------------------------------------------------

        abilities_blocks = _section(
            parsed.sections,
            ABILITIES_HEADINGS,
        ) or []

        abilities = _extract_abilities(abilities_blocks)

        # --------------------------------------------------
        # Mechanics
        # --------------------------------------------------

        mechanics_blocks = _section(
            parsed.sections,
            MECHANICS_HEADINGS,
        ) or []

        mechanics = _extract_mechanics(mechanics_blocks)

        # --------------------------------------------------
        # Strategy
        # --------------------------------------------------

        strategy_blocks = _section(
            parsed.sections,
            STRATEGY_HEADINGS,
        ) or []

        strategy_paragraphs = [
            b["text"]
            for b in strategy_blocks
            if b["type"] == "p" and b["text"].strip()
        ]

        # --------------------------------------------------
        # Phases
        # --------------------------------------------------
        # UESP can describe named phases inside Skills and
        # Abilities rather than the Strategy section.

        phases = _extract_phases(abilities_blocks)

        # --------------------------------------------------
        # Dialogue
        # --------------------------------------------------

        dialogue_blocks = _section(parsed.sections, DIALOGUE_HEADINGS) or []
        dialogue = _extract_dialogue(dialogue_blocks)

        dialogue_by_trigger = _group_dialogue_by_trigger(dialogue)

        # Match each dialogue trigger to an ability only when the page
        # provides enough textual evidence. Unknown relationships remain None.
        for trigger, entries in dialogue_by_trigger.items():
            matched_ability = _match_dialogue_trigger_to_ability(
                trigger,
                entries,
                abilities,
            )
            for entry in entries:
                entry.ability = matched_ability
        # --------------------------------------------------
        # Notes / related information
        # --------------------------------------------------

        notes = _extract_list_text(
            _section(parsed.sections, NOTES_HEADINGS) or []
        )

        related_quests = _extract_list_text(
            _section(parsed.sections, QUEST_HEADINGS) or []
        )

        related_npcs = _extract_list_text(
            _section(parsed.sections, NPC_HEADINGS) or []
        )

        # --------------------------------------------------
        # Difficulty notes
        # --------------------------------------------------

        all_paragraphs = [
            b["text"]
            for b in parsed.all_blocks
            if b["type"] == "p" and b["text"].strip()
        ]

        difficulty_notes = _extract_difficulty_notes(all_paragraphs)

        # --------------------------------------------------
        # Achievement references
        # --------------------------------------------------

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
            health=_extract_health(
                next(
                    (
                        block["cells"][1]
                        for block in parsed.all_blocks
                        if block.get("type") == "tr"
                        and block.get("cells")
                        and block["cells"][0].get("text", "").strip().lower() == "health"
                        and len(block["cells"]) >= 2
                    ),
                    {"text": "", "links": []},
                )
            ),
            abilities=abilities,
            mechanics=mechanics,
            phases=phases,
            dialogue=dialogue,
            dialogue_by_trigger=dialogue_by_trigger,
            difficulty_notes=difficulty_notes,
            strategy_notes=strategy_paragraphs,
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

    def parse_content(self, page: UespPage, content_type: str) -> UespContent:

        parsed = parse_page_html(page.html)

        achievement_refs = _extract_linked_titles(
            _section(parsed.sections, ACHIEVEMENT_HEADINGS) or []
        )
        notes = _extract_list_text(_section(parsed.sections, NOTES_HEADINGS) or [])
        related_npcs = _extract_list_text(_section(parsed.sections, NPC_HEADINGS) or [])

        return UespContent(
            id=slugify(page.title),
            name=_clean_title(page.title),
            content_type=content_type,
            summary=parsed.summary,
            location=parsed.infobox.get("location", ""),
            achievements=[
                UespAchievement(id=slugify(title), name=display_text)
                for display_text, title in achievement_refs
            ],
            related_npcs=related_npcs,
            notes=notes,
            source=_source_for(page),
        )

    def parse_achievement(self, page: UespPage) -> UespAchievement:
        parsed = parse_page_html(page.html)
        return UespAchievement(
            id=slugify(page.title),
            name=_clean_title(page.title),
            description=parsed.summary,
            source=_source_for(page),
        )

    
    @staticmethod
    def _dedupe_titles(titles: list[str]) -> list[str]:
        """
        Remove duplicate wiki titles while preserving their original order.
        Matching is case-insensitive so one wiki page cannot be imported twice.
        """
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
        """
        Discover boss pages from an explicit Bosses/Encounters section.

        This intentionally does NOT fall back to every link on the page.
        UESP overview pages contain links to locations, NPCs, achievements,
        abilities, items, lore, and other pages. Treating those as bosses was
        the source of the Blackrose Prison garbage import.

        If there is no explicit boss section, return [] rather than guessing.
        """
        parsed = parse_page_html(page.html)

        blocks = _section(
            parsed.sections,
            BOSS_SECTION_HEADINGS,
        )

        if not blocks:
            return []

        candidates = [
            title
            for _, title in _extract_linked_titles(blocks)
            if title.strip()
        ]

        excluded_words = (
            "achievement",
            "achievements",
            "quest",
            "quests",
            "item",
            "set",
            "style",
            "furnishing",
            "collectible",
            "monster",
            "npc",
            "location",
            "zone",
            "guide",
            "strategy",
            "journal",
        )

        generic_pages = {
            "arenas",
            "dungeons",
            "trials",
            "murkmire",
            "dead water village",
            "imperial",
            "blackguards",
        }

        filtered: list[str] = []

        for title in candidates:
            lowered = title.casefold()

            if lowered in generic_pages:
                continue

            if any(word in lowered for word in excluded_words):
                continue

            filtered.append(title)

        return self._dedupe_titles(filtered)


    def detect_content_type(
        self,
        page: UespPage,
        default: str,
    ) -> str:
        """
        Infer trial/dungeon/arena from the page's UESP categories.

        If no matching category is present, preserve the caller's
        supplied default.
        """

        categories_lower = {
            category.lower()
            for category in page.categories
        }

        if any("dungeon" in category for category in categories_lower):
            return "dungeon"

        if any("arena" in category for category in categories_lower):
            return "arena"

        if any("trial" in category for category in categories_lower):
            return "trial"

        return default
