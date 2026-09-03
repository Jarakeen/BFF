from __future__ import annotations

"""Stage user-collected encounter research without promoting it to canonical truth.

The importer accepts a ZIP archive plus the existing ESO database. Textual source
material is normalized just enough to identify persisted encounter names and
extract review candidates. Original source files remain outside the canonical
encounter database; every staged candidate retains its source member/hash and a
short evidence excerpt.

This module deliberately does *not* translate source text, resolve conflicts,
write encounter_canonical_fact, or infer strategies from images.
"""

from dataclasses import dataclass, asdict
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterable
import zipfile


TEXT_EXTENSIONS = {".txt", ".md", ".htm", ".html", ""}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".avif"}

_DATA_URI_RE = re.compile(
    r"data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=\r\n]+",
    re.IGNORECASE,
)
_SPACE_RE = re.compile(r"[ \t]+")
_PERCENT_RE = re.compile(r"(?<!\d)(\d{1,3})\s*%")
_TIME_RE = re.compile(
    r"(?i)\b(\d+(?:\.\d+)?)\s*(seconds?|secs?|sec|s|minutes?|mins?|min|m)\b"
)
_APPROX_RE = re.compile(r"(?i)\b(?:about|around|approximately|approx\.?|roughly|nearly)\b|~")
_CANDIDATE_CUE_RE = re.compile(
    r"(?i)\b(?:phase|intermission|threshold|execute|enrage|"
    r"spawn(?:s|ed|ing)?|summon(?:s|ed|ing)?|appears?|enters?|adds?|"
    r"interrupt(?:ed|ible|ing)?|bash|block(?:ed|ing)?|dodge(?:d|roll)?|"
    r"cleanse(?:d|s)?|purge(?:d|s)?|spread|stack|move(?:s|d|ment)?|"
    r"position(?:s|ed|ing)?|portal|kite|bait|"
    r"invulnerable|untargetable|immune|shield|one[- ]shot|fatal|wipe|kill)\b"
)
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")

_LANGUAGE_WORDS = {
    "en": {"the", "and", "when", "player", "boss", "will", "damage", "phase", "health", "seconds"},
    "fr": {"le", "la", "les", "et", "quand", "joueur", "boss", "dégâts", "phase", "santé", "secondes"},
    "it": {"il", "la", "gli", "e", "quando", "giocatore", "boss", "danni", "fase", "salute", "secondi"},
}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.language = ""
        self.canonical_url = ""
        self.title = ""
        self._in_title = False
        self._ignored_depth = 0
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = {str(k).casefold(): str(v or "") for k, v in attrs}
        tag = tag.casefold()
        if tag == "html":
            self.language = values.get("lang", "")
        if tag == "link" and "canonical" in values.get("rel", "").casefold():
            self.canonical_url = values.get("href", "")
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br"}:
            self._text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
        if tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._text.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._in_title:
            self.title += data
        self._text.append(data)

    @property
    def text(self) -> str:
        return "".join(self._text)


@dataclass(frozen=True)
class EncounterResearchSource:
    source_id: str
    archive_member: str
    sha256: str
    byte_count: int
    media_type: str
    language: str
    title: str
    source_url: str
    source_name: str
    content_hint: str
    encounter_hint: str


@dataclass(frozen=True)
class EncounterResearchCandidate:
    candidate_id: str
    source_id: str
    encounter_id: str
    encounter_name: str
    content_id: str
    content_name: str
    source_language: str
    source_locator: str
    event_type: str
    trigger_type: str
    trigger_value: str
    approximate: bool
    evidence_text: str
    interpretation_status: str = "pending_review"


@dataclass(frozen=True)
class EncounterResearchBundle:
    schema_version: int
    archive_sha256: str
    sources: tuple[EncounterResearchSource, ...]
    candidates: tuple[EncounterResearchCandidate, ...]
    unmatched_candidates: int
    visual_sources: int

    def to_json_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "archive_sha256": self.archive_sha256,
            "sources": [asdict(row) for row in self.sources],
            "candidates": [asdict(row) for row in self.candidates],
            "unmatched_candidates": self.unmatched_candidates,
            "visual_sources": self.visual_sources,
        }


@dataclass(frozen=True)
class _EncounterIdentity:
    encounter_id: str
    encounter_name: str
    content_id: str
    content_name: str


@dataclass(frozen=True)
class _ManifestRow:
    archive_member: str
    sha256: str
    source_name: str = ""
    language: str = ""
    source_url: str = ""
    content_hint: str = ""
    encounter_hint: str = ""


def _clean_line(value: str) -> str:
    return _SPACE_RE.sub(" ", value.replace("\r", " ")).strip()


def _normalized_identity(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _archive_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _media_type(member: str) -> str:
    suffix = Path(member).suffix.casefold()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in {".htm", ".html"}:
        return "html"
    if suffix == ".md":
        return "markdown"
    return "text"


def _detect_language(text: str, explicit: str = "") -> str:
    explicit = explicit.strip().casefold().replace("_", "-")
    if explicit:
        prefix = explicit.split("-", 1)[0]
        if prefix in _LANGUAGE_WORDS:
            return prefix

    words = re.findall(r"[A-Za-zÀ-ÿ']+", text.casefold())[:5000]
    counts = {language: 0 for language in _LANGUAGE_WORDS}
    for word in words:
        for language, vocabulary in _LANGUAGE_WORDS.items():
            counts[language] += int(word in vocabulary)
    best = max(counts, key=counts.get)
    return best if counts[best] >= 3 else "unknown"


def _decode_text(member: str, data: bytes) -> tuple[str, str, str, str]:
    """Return normalized text, explicit language, title, canonical URL."""
    raw = data.decode("utf-8", errors="ignore")
    raw = _DATA_URI_RE.sub("[embedded image removed]", raw)
    suffix = Path(member).suffix.casefold()
    if suffix in {".htm", ".html"}:
        parser = _HTMLTextExtractor()
        parser.feed(raw)
        return parser.text, parser.language, _clean_line(parser.title), parser.canonical_url.strip()
    return raw, "", "", ""


def _load_manifest(path: Path | None) -> dict[str, _ManifestRow]:
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise ValueError("encounter research manifest must contain a sources array")
    rows: dict[str, _ManifestRow] = {}
    for raw in payload["sources"]:
        if not isinstance(raw, dict):
            raise ValueError("encounter research manifest source rows must be objects")
        member = str(raw.get("archive_member") or "").strip()
        if not member:
            raise ValueError("encounter research manifest row is missing archive_member")
        if member in rows:
            raise ValueError(f"duplicate encounter research manifest member: {member}")
        rows[member] = _ManifestRow(
            archive_member=member,
            sha256=str(raw.get("sha256") or "").strip().casefold(),
            source_name=str(raw.get("source_name") or "").strip(),
            language=str(raw.get("language") or "").strip().casefold(),
            source_url=str(raw.get("source_url") or "").strip(),
            content_hint=str(raw.get("content_hint") or "").strip(),
            encounter_hint=str(raw.get("encounter_hint") or "").strip(),
        )
    return rows


def _encounters(database: Path) -> tuple[_EncounterIdentity, ...]:
    database = Path(database)
    if not database.exists():
        raise FileNotFoundError(f"encounter database does not exist: {database}")
    connection = sqlite3.connect(database)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if not {"encounter", "content"}.issubset(tables):
            raise RuntimeError("encounter database is missing encounter/content tables")
        return tuple(
            _EncounterIdentity(
                encounter_id=str(row[0]),
                encounter_name=str(row[1]),
                content_id=str(row[2]),
                content_name=str(row[3]),
            )
            for row in connection.execute(
                """
                SELECT e.id, e.name, e.content_id, c.name
                FROM encounter AS e
                JOIN content AS c ON c.id=e.content_id
                ORDER BY length(e.name) DESC, e.name COLLATE NOCASE
                """
            ).fetchall()
        )
    finally:
        connection.close()


def _encounter_lookup(encounters: Iterable[_EncounterIdentity]) -> tuple[dict[str, _EncounterIdentity], dict[str, _EncounterIdentity]]:
    by_id: dict[str, _EncounterIdentity] = {}
    by_name: dict[str, _EncounterIdentity] = {}
    for row in encounters:
        by_id[_normalized_identity(row.encounter_id)] = row
        by_name[_normalized_identity(row.encounter_name)] = row
    return by_id, by_name


def _manifest_encounter(row: _ManifestRow | None, by_id, by_name) -> _EncounterIdentity | None:
    if row is None or not row.encounter_hint:
        return None
    key = _normalized_identity(row.encounter_hint)
    return by_id.get(key) or by_name.get(key)


def _encounter_in_text(text: str, encounters: Iterable[_EncounterIdentity]) -> _EncounterIdentity | None:
    normalized = f" {_normalized_identity(text)} "
    for row in encounters:
        name = _normalized_identity(row.encounter_name)
        if len(name) < 4:
            continue
        if f" {name} " in normalized:
            return row
    return None


def _event_type(text: str) -> str:
    lowered = text.casefold()
    if "interrupt" in lowered or "bash" in lowered:
        return "interrupt"
    if "cleanse" in lowered or "purge" in lowered:
        return "cleanse"
    if any(word in lowered for word in ("dodge", "move", "kite")):
        return "movement"
    if any(word in lowered for word in ("position", "stack", "spread", "bait")):
        return "positioning"
    if any(word in lowered for word in ("spawn", "summon", " add ", " adds ")):
        return "adds"
    if any(word in lowered for word in ("one-shot", "one shot", "fatal", "wipe", "enrage")):
        return "danger"
    if any(word in lowered for word in ("phase", "intermission", "threshold", "execute")):
        return "phase"
    return "mechanic"


def _trigger_rows(text: str) -> list[tuple[str, str, bool]]:
    approximate = bool(_APPROX_RE.search(text))
    rows: list[tuple[str, str, bool]] = []
    lowered = text.casefold()
    for value in _PERCENT_RE.findall(text):
        trigger = "boss_health" if (
            "health" in lowered
            or " hp" in lowered
            or re.search(rf"(?i)\b(?:at|reaches?|below|under|above)\s+{re.escape(value)}\s*%", text)
        ) else "percent_unspecified"
        rows.append((trigger, f"{value}%", approximate))

    for value, unit in _TIME_RE.findall(text):
        unit = unit.casefold()
        normalized_unit = "seconds" if unit.startswith("s") else "minutes"
        if re.search(r"(?i)\bevery\b", text):
            trigger = "repeat_interval"
        elif re.search(r"(?i)\bafter\b", text):
            trigger = "elapsed_after"
        elif re.search(r"(?i)\b(?:for|lasts?|duration)\b", text):
            trigger = "duration"
        else:
            trigger = "time_unspecified"
        rows.append((trigger, f"{value} {normalized_unit}", approximate))

    if not rows and _CANDIDATE_CUE_RE.search(text):
        rows.append(("ordering_or_condition", "", approximate))
    return rows


def _candidate_lines(text: str) -> Iterable[tuple[str, bool]]:
    """Yield normalized logical blocks and whether each was a Markdown heading."""
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        heading_match = _HEADING_RE.match(raw)
        if heading_match:
            yield _clean_line(heading_match.group(1)), True
            continue
        line = _clean_line(raw)
        if len(line) >= 12:
            yield line, False


def _candidate_id(source_id: str, encounter_id: str, event_type: str, trigger_type: str, trigger_value: str, evidence: str) -> str:
    payload = "\n".join((source_id, encounter_id, event_type, trigger_type, trigger_value, evidence))
    return sha256(payload.encode("utf-8")).hexdigest()[:24]


def import_research_archive(
    archive: Path,
    database: Path,
    *,
    manifest_path: Path | None = None,
) -> EncounterResearchBundle:
    archive = Path(archive)
    manifest = _load_manifest(manifest_path)
    encounter_rows = _encounters(database)
    by_id, by_name = _encounter_lookup(encounter_rows)

    sources: list[EncounterResearchSource] = []
    candidates: list[EncounterResearchCandidate] = []
    unmatched = 0
    visuals = 0

    with zipfile.ZipFile(archive) as zipped:
        for info in zipped.infolist():
            if info.is_dir():
                continue
            member = info.filename
            short_member = member.split("/", 1)[-1]
            raw = zipped.read(info)
            digest = sha256(raw).hexdigest()
            manifest_row = manifest.get(short_member) or manifest.get(member)
            if manifest_row is not None and manifest_row.sha256 and manifest_row.sha256 != digest:
                raise RuntimeError(
                    f"encounter research archive member hash mismatch: {short_member}"
                )

            media_type = _media_type(short_member)
            if media_type == "image":
                visuals += 1
                source_id = f"research:{digest[:20]}"
                sources.append(
                    EncounterResearchSource(
                        source_id=source_id,
                        archive_member=short_member,
                        sha256=digest,
                        byte_count=len(raw),
                        media_type=media_type,
                        language=(manifest_row.language if manifest_row else "") or "non_text",
                        title=Path(short_member).stem,
                        source_url=(manifest_row.source_url if manifest_row else ""),
                        source_name=(manifest_row.source_name if manifest_row else "") or "User research archive",
                        content_hint=(manifest_row.content_hint if manifest_row else ""),
                        encounter_hint=(manifest_row.encounter_hint if manifest_row else ""),
                    )
                )
                continue

            text, explicit_language, title, canonical_url = _decode_text(short_member, raw)
            language = (
                (manifest_row.language if manifest_row else "")
                or _detect_language(text, explicit_language)
            )
            source_id = f"research:{digest[:20]}"
            source = EncounterResearchSource(
                source_id=source_id,
                archive_member=short_member,
                sha256=digest,
                byte_count=len(raw),
                media_type=media_type,
                language=language,
                title=title or Path(short_member).stem,
                source_url=(manifest_row.source_url if manifest_row else "") or canonical_url,
                source_name=(manifest_row.source_name if manifest_row else "") or "User research archive",
                content_hint=(manifest_row.content_hint if manifest_row else ""),
                encounter_hint=(manifest_row.encounter_hint if manifest_row else ""),
            )
            sources.append(source)

            current_encounter = _manifest_encounter(manifest_row, by_id, by_name)
            file_encounter = current_encounter or _encounter_in_text(Path(short_member).stem, encounter_rows)
            if file_encounter is not None:
                current_encounter = file_encounter

            for line, is_heading in _candidate_lines(text):
                named_encounter = _encounter_in_text(line, encounter_rows)
                if named_encounter is not None:
                    current_encounter = named_encounter
                    if is_heading or len(line) <= 180:
                        # Encounter headings establish context but are not facts by themselves.
                        if not (_PERCENT_RE.search(line) or _TIME_RE.search(line) or _CANDIDATE_CUE_RE.search(line)):
                            continue

                triggers = _trigger_rows(line)
                if not triggers:
                    continue
                if current_encounter is None:
                    unmatched += len(triggers)
                    continue

                event_type = _event_type(line)
                evidence = line[:600]
                for trigger_type, trigger_value, approximate in triggers:
                    candidate_id = _candidate_id(
                        source_id,
                        current_encounter.encounter_id,
                        event_type,
                        trigger_type,
                        trigger_value,
                        evidence,
                    )
                    candidates.append(
                        EncounterResearchCandidate(
                            candidate_id=candidate_id,
                            source_id=source_id,
                            encounter_id=current_encounter.encounter_id,
                            encounter_name=current_encounter.encounter_name,
                            content_id=current_encounter.content_id,
                            content_name=current_encounter.content_name,
                            source_language=language,
                            source_locator=source.source_url or short_member,
                            event_type=event_type,
                            trigger_type=trigger_type,
                            trigger_value=trigger_value,
                            approximate=approximate,
                            evidence_text=evidence,
                        )
                    )

    # Stable de-duplication protects repeated identical prose within saved pages.
    unique_candidates = {row.candidate_id: row for row in candidates}
    return EncounterResearchBundle(
        schema_version=1,
        archive_sha256=_archive_sha256(archive),
        sources=tuple(sources),
        candidates=tuple(unique_candidates[key] for key in sorted(unique_candidates)),
        unmatched_candidates=unmatched,
        visual_sources=visuals,
    )


def write_research_bundle(bundle: EncounterResearchBundle, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(bundle.to_json_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path
