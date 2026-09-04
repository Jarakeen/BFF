from __future__ import annotations

"""Persistent, user-owned encounter research intake state.

Imported guide/source files are copied beneath ``data/encounter_research`` and
converted into conservative review candidates. Nothing in this module writes to
canonical encounter tables. Approved candidates remain review-layer material
until a later explicit evidence/promotion step consumes them.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import uuid
import zipfile

from services.encounter_evidence import EncounterEvidence


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".html", ".htm"}
SUPPORTED_MAP_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_SUFFIXES = SUPPORTED_TEXT_SUFFIXES | SUPPORTED_MAP_SUFFIXES
STATUS_VALUES = {"pending", "approved", "rejected", "deferred"}

_DATA_URL_RE = re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=\r\n]+", re.IGNORECASE)
_PERCENT_RE = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*%")
_TIME_RE = re.compile(r"\b(?:(\d{1,2}):([0-5]\d)|(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s))\b", re.IGNORECASE)
_PHASE_RE = re.compile(r"\bphase\s+(\d+|one|two|three|four|five|six)\b", re.IGNORECASE)
_ADD_RE = re.compile(r"\b(adds?|summons?|spawns?)\b", re.IGNORECASE)
_INTERRUPT_RE = re.compile(r"\b(interrupt|bash|interruptible)\b", re.IGNORECASE)
_POSITION_RE = re.compile(r"\b(stack|spread|position|positioning|move|kite|portal|dome|bridge)\b", re.IGNORECASE)


@dataclass(frozen=True)
class EncounterResearchSource:
    source_id: str
    original_name: str
    stored_path: str
    sha256: str
    imported_at: str
    source_type: str
    language: str
    content_hint: str
    encounter_hint: str


@dataclass(frozen=True)
class EncounterResearchCandidate:
    candidate_id: str
    source_id: str
    content_id: str
    encounter_id: str
    fact_type: str
    fact_key: str
    value: object
    evidence_text: str
    status: str
    reviewer_note: str = ""


class EncounterResearchStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.root = self.data_dir / "encounter_research"
        self.sources_dir = self.root / "sources"
        self.state_path = self.root / "research_state.json"
        self.sources_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return {"schema_version": 1, "sources": [], "candidates": []}
        if not isinstance(payload, dict):
            return {"schema_version": 1, "sources": [], "candidates": []}
        payload.setdefault("schema_version", 1)
        payload.setdefault("sources", [])
        payload.setdefault("candidates", [])
        return payload

    def _save(self, payload: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def sources(self) -> tuple[EncounterResearchSource, ...]:
        rows = []
        for raw in self._load().get("sources", []):
            try:
                rows.append(EncounterResearchSource(**raw))
            except TypeError:
                continue
        return tuple(rows)

    def candidates(self) -> tuple[EncounterResearchCandidate, ...]:
        rows = []
        for raw in self._load().get("candidates", []):
            try:
                rows.append(EncounterResearchCandidate(**raw))
            except TypeError:
                continue
        return tuple(rows)

    def counts(self) -> dict[str, int]:
        result = {status: 0 for status in STATUS_VALUES}
        for row in self.candidates():
            result[row.status] = result.get(row.status, 0) + 1
        result["sources"] = len(self.sources())
        result["candidates"] = sum(result.get(status, 0) for status in STATUS_VALUES)
        return result

    def approved_evidence(self) -> tuple[EncounterEvidence, ...]:
        """Expose approved, boss-assigned candidates to existing reconciliation.

        This is an adapter only. It does not write evidence packets or canonical
        facts. Candidates without an encounter id stay in Research until the
        reviewer assigns them to a boss.
        """
        sources = {row.source_id: row for row in self.sources()}
        rows: list[EncounterEvidence] = []
        for candidate in self.candidates():
            if candidate.status != "approved" or not candidate.encounter_id.strip():
                continue
            source = sources.get(candidate.source_id)
            if source is None:
                continue
            rows.append(
                EncounterEvidence(
                    encounter_id=candidate.encounter_id,
                    fact_type=candidate.fact_type,
                    fact_key=candidate.fact_key,
                    value=candidate.value,
                    source_type=source.source_type,
                    source_name=source.original_name,
                    source_locator=source.stored_path,
                    source_revision=source.sha256,
                    source_family=source.sha256,
                    confidence="medium",
                    notes=candidate.reviewer_note or candidate.evidence_text,
                )
            )
        return tuple(rows)

    @staticmethod
    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _source_type(path: Path) -> str:
        return "raid_map" if path.suffix.lower() in SUPPORTED_MAP_SUFFIXES else "community_guide"

    @staticmethod
    def _safe_label(value: str) -> str:
        text = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(value or "").strip()).strip("._")
        return text or "source"

    def _copy_source(self, source: Path) -> Path:
        digest = self._digest(source)
        folder = self.sources_dir / digest[:12]
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / self._safe_label(source.name)
        if not destination.exists():
            shutil.copy2(source, destination)
        return destination

    def import_path(
        self,
        path: Path,
        *,
        content_hint: str = "",
        encounter_hint: str = "",
        language: str = "unknown",
    ) -> tuple[EncounterResearchSource, ...]:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)
        if source.suffix.lower() == ".zip":
            return self._import_zip(
                source,
                content_hint=content_hint,
                encounter_hint=encounter_hint,
                language=language,
            )
        if source.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported encounter research file type: {source.suffix or '<none>'}")
        return (
            self._register_source(
                source,
                content_hint=content_hint,
                encounter_hint=encounter_hint,
                language=language,
            ),
        )

    def _import_zip(
        self,
        archive: Path,
        *,
        content_hint: str,
        encounter_hint: str,
        language: str,
    ) -> tuple[EncounterResearchSource, ...]:
        imported = []
        extract_root = self.root / "zip_staging" / uuid.uuid4().hex
        extract_root.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive) as bundle:
                for info in bundle.infolist():
                    if info.is_dir():
                        continue
                    member = PurePosixPath(info.filename)
                    if member.is_absolute() or ".." in member.parts:
                        continue
                    if member.suffix.lower() not in SUPPORTED_SUFFIXES:
                        continue
                    destination = extract_root.joinpath(*member.parts)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(info) as src, destination.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    imported.append(
                        self._register_source(
                            destination,
                            original_name=member.as_posix(),
                            content_hint=content_hint,
                            encounter_hint=encounter_hint,
                            language=language,
                        )
                    )
        finally:
            shutil.rmtree(extract_root, ignore_errors=True)
        return tuple(imported)

    def _register_source(
        self,
        source: Path,
        *,
        original_name: str | None = None,
        content_hint: str,
        encounter_hint: str,
        language: str,
    ) -> EncounterResearchSource:
        digest = self._digest(source)
        existing = next((row for row in self.sources() if row.sha256 == digest), None)
        if existing is not None:
            return existing

        destination = self._copy_source(source)
        row = EncounterResearchSource(
            source_id=uuid.uuid4().hex,
            original_name=original_name or source.name,
            stored_path=str(destination.relative_to(self.data_dir)).replace("\\", "/"),
            sha256=digest,
            imported_at=datetime.now(timezone.utc).isoformat(),
            source_type=self._source_type(source),
            language=str(language or "unknown").strip() or "unknown",
            content_hint=str(content_hint or "").strip(),
            encounter_hint=str(encounter_hint or "").strip(),
        )

        payload = self._load()
        payload["sources"].append(asdict(row))
        payload["candidates"].extend(asdict(candidate) for candidate in self._extract_candidates(row))
        self._save(payload)
        return row

    def _extract_candidates(
        self,
        source: EncounterResearchSource,
    ) -> tuple[EncounterResearchCandidate, ...]:
        path = self.data_dir / source.stored_path
        if path.suffix.lower() in SUPPORTED_MAP_SUFFIXES:
            return (
                EncounterResearchCandidate(
                    candidate_id=uuid.uuid4().hex,
                    source_id=source.source_id,
                    content_id=source.content_hint,
                    encounter_id=source.encounter_hint,
                    fact_type="map",
                    fact_key=path.stem,
                    value={"stored_path": source.stored_path, "label": path.stem},
                    evidence_text=source.original_name,
                    status="pending",
                ),
            )

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ()
        text = _DATA_URL_RE.sub("[embedded image removed]", text)

        candidates: list[EncounterResearchCandidate] = []
        seen: set[tuple[str, str, str]] = set()
        for raw_line in text.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if len(line) < 8 or len(line) > 700:
                continue

            matches: list[tuple[str, str, object]] = []
            for percent in _PERCENT_RE.findall(line):
                matches.append(("transition", "health_threshold", {"threshold": f"{percent}%"}))
            phase = _PHASE_RE.search(line)
            if phase:
                matches.append(("phase", "phase", {"label": f"Phase {phase.group(1)}"}))
            if _INTERRUPT_RE.search(line):
                matches.append(("interrupt", "interrupt", {"required": True}))
            if _ADD_RE.search(line):
                matches.append(("mechanic", "adds", {"adds": True}))
            if _POSITION_RE.search(line):
                matches.append(("positioning", "positioning", {"positioning": True}))

            time_match = _TIME_RE.search(line)
            if time_match:
                if time_match.group(1) is not None:
                    seconds = int(time_match.group(1)) * 60 + int(time_match.group(2))
                else:
                    seconds = float(time_match.group(3))
                matches.append(("transition", "exact_time", {"time_seconds": seconds}))

            for fact_type, fact_key, value in matches:
                key = (fact_type, fact_key, json.dumps(value, sort_keys=True))
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    EncounterResearchCandidate(
                        candidate_id=uuid.uuid4().hex,
                        source_id=source.source_id,
                        content_id=source.content_hint,
                        encounter_id=source.encounter_hint,
                        fact_type=fact_type,
                        fact_key=fact_key,
                        value=value,
                        evidence_text=line,
                        status="pending",
                    )
                )
        return tuple(candidates)

    def set_candidate_status(
        self,
        candidate_id: str,
        status: str,
        *,
        reviewer_note: str = "",
    ) -> EncounterResearchCandidate:
        normalized = str(status or "").strip().casefold()
        if normalized not in STATUS_VALUES:
            raise ValueError(f"Unsupported review status: {status!r}")
        payload = self._load()
        for index, raw in enumerate(payload.get("candidates", [])):
            if str(raw.get("candidate_id", "")) != candidate_id:
                continue
            raw = dict(raw)
            raw["status"] = normalized
            raw["reviewer_note"] = str(reviewer_note or "")
            payload["candidates"][index] = raw
            self._save(payload)
            return EncounterResearchCandidate(**raw)
        raise KeyError(f"Unknown encounter research candidate: {candidate_id}")
