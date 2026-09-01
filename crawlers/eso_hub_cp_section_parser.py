from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag


def _normalize_text(value: Any) -> str:
    text = str(value or "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_name(value: Any) -> str:
    text = _normalize_text(value).lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _heading_tag(soup: BeautifulSoup, skill_name: str) -> Tag | None:
    expected = _normalize_name(f"Champion Points that buff {skill_name}")

    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        if _normalize_name(tag.get_text(" ", strip=True)) == expected:
            return tag

    for node in soup.find_all(string=True):
        if _normalize_name(node) != expected:
            continue
        if isinstance(node.parent, Tag):
            return node.parent

    return None


def _condition_from_container(tag: Tag, cp_name: str) -> str | None:
    container = tag.find_parent(["li", "p", "div"]) or tag.parent
    text = _normalize_text(container.get_text(" ", strip=True) if isinstance(container, Tag) else "")
    if not text:
        return None

    cp_text = _normalize_text(cp_name)
    if text.lower().startswith(cp_text.lower()):
        text = text[len(cp_text):].strip()

    match = re.search(r"\(([^()]+)\)", text)
    if match:
        return _normalize_text(match.group(1)) or None

    if _normalize_name(text) == "only while slotted":
        return "only while slotted"
    return None


def extract_current_cp_section(
    soup: BeautifulSoup,
    skill_name: str,
    cp_vocab: dict[str, dict],
) -> tuple[list[dict], str | None]:
    """Extract explicit CP links from the current ESO-Hub skill-page layout.

    ESO-Hub currently renders the CP section as ordinary text followed by linked
    CP names, with qualifiers such as ``(only while slotted)`` inline. We anchor
    on the exact ``Champion Points that buff <skill>`` text, then scan forward
    only until the next semantic section heading. A name must exist in the
    canonical CP vocabulary before it can be emitted.
    """

    heading = _heading_tag(soup, skill_name)
    if heading is None:
        return [], "CP section not found"

    results: list[dict] = []
    seen: set[str] = set()

    for tag in heading.find_all_next(True):
        if tag is heading:
            continue

        if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            break

        # ESO-Hub has also used non-heading labels for these boundaries.
        text = _normalize_text(tag.get_text(" ", strip=True))
        normalized_text = _normalize_name(text)
        if normalized_text in {
            "unmorphed version",
            "other morph",
            "top builds using " + _normalize_name(skill_name),
        }:
            break

        if tag.name != "a":
            continue

        visible = _normalize_text(tag.get_text(" ", strip=True))
        key = _normalize_name(visible)
        if key not in cp_vocab or key in seen:
            continue

        cp_record = cp_vocab[key]
        results.append(
            {
                "champion_point_id": cp_record.get("id"),
                "champion_point_name": cp_record.get("name") or visible,
                "condition": _condition_from_container(tag, visible),
                "source": "ESO-Hub",
            }
        )
        seen.add(key)

    return results, None
