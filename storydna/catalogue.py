"""Catalogue loading and validation (JSON list or CSV). Fails with readable messages, never a stack trace."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

from .textproc import split_sentences

MAX_TEXT_CHARS = 200_000
MAX_CARDS = 20_000
REQUIRED = ("story_id", "title", "synopsis")


class InputError(ValueError):
    """Raised for bad user input; message is safe to show in the UI."""


@dataclass
class StoryCard:
    story_id: str
    title: str
    synopsis: str
    genre: str = ""
    source_url: str = ""
    provenance: str = ""
    language: str = "en"
    beats: list[str] = field(default_factory=list)
    original_synopsis: str = ""                       # set when the synopsis was translated for matching
    beats_original: list[str] = field(default_factory=list)   # source-language sentence per English beat

    def __post_init__(self):
        if not self.beats:
            self.beats = split_sentences(self.synopsis)

    @property
    def granularity(self) -> str:
        n = len(self.beats)
        return "synopsis-only (%d beats)" % n if n < 15 else "detailed outline (%d beats)" % n


def clean_pitch(text: str) -> str:
    if text is None or not str(text).strip():
        raise InputError("The pitch is empty. Paste at least a few sentences describing the story's events.")
    text = str(text)
    if len(text) > MAX_TEXT_CHARS:
        raise InputError(
            "The pitch is %d characters long (limit %d). Summarise it to a synopsis or outline first."
            % (len(text), MAX_TEXT_CHARS)
        )
    # Strip control chars but keep newlines.
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    if not split_sentences(text):
        raise InputError("No readable sentences found in the pitch.")
    return text


def _cards_from_rows(rows: list[dict]) -> list[StoryCard]:
    if not rows:
        raise InputError("The catalogue is empty. It needs at least one story card.")
    if len(rows) > MAX_CARDS:
        raise InputError("The catalogue has %d cards; this prototype supports up to %d." % (len(rows), MAX_CARDS))
    cards: list[StoryCard] = []
    seen: set[str] = set()
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise InputError("Catalogue row %d is not an object/record." % i)
        missing = [k for k in REQUIRED if not str(row.get(k, "")).strip()]
        if missing:
            raise InputError("Catalogue row %d is missing required field(s): %s." % (i, ", ".join(missing)))
        sid = str(row["story_id"]).strip()
        if sid in seen:
            raise InputError("Duplicate story_id %r in catalogue (row %d)." % (sid, i))
        seen.add(sid)
        if len(str(row["synopsis"])) > MAX_TEXT_CHARS:
            raise InputError("Synopsis for %s is too long (limit %d characters)." % (sid, MAX_TEXT_CHARS))
        beats = row.get("plot_beats")
        if isinstance(beats, str):
            beats = [b for b in beats.split("|") if b.strip()]
        cards.append(StoryCard(
            story_id=sid, title=str(row["title"]).strip(), synopsis=str(row["synopsis"]).strip(),
            genre=str(row.get("genre", "") or ""), source_url=str(row.get("source_url", "") or ""),
            provenance=str(row.get("provenance", "") or ""), language=str(row.get("language", "en") or "en"),
            beats=[str(b).strip() for b in (beats or [])],
        ))
    return cards


def parse_catalogue(raw: bytes | str, filename: str = "catalogue.json") -> list[StoryCard]:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise InputError("The catalogue file is not valid UTF-8 text.")
    name = filename.lower()
    if name.endswith(".csv"):
        try:
            reader = csv.DictReader(io.StringIO(raw))
            if not reader.fieldnames or not all(k in reader.fieldnames for k in REQUIRED):
                raise InputError(
                    "CSV header must contain: %s. Found: %s." % (", ".join(REQUIRED), reader.fieldnames)
                )
            rows = list(reader)
        except csv.Error as e:
            raise InputError("Could not parse the CSV catalogue: %s" % e)
    else:
        try:
            rows = json.loads(raw)
        except json.JSONDecodeError as e:
            raise InputError("Could not parse the JSON catalogue (line %d, column %d): %s" % (e.lineno, e.colno, e.msg))
        if isinstance(rows, dict) and "stories" in rows:
            rows = rows["stories"]
        if not isinstance(rows, list):
            raise InputError("A JSON catalogue must be a list of story objects.")
    return _cards_from_rows(rows)


def load_catalogue(path: str | Path) -> list[StoryCard]:
    p = Path(path)
    if not p.exists():
        raise InputError("Catalogue file not found: %s" % p)
    return parse_catalogue(p.read_bytes(), p.name)


def catalogue_fingerprint(cards: list[StoryCard]) -> str:
    h = hashlib.sha256()
    for c in cards:
        h.update(("%s|%s|%s\n" % (c.story_id, c.title, c.synopsis)).encode("utf-8"))
    return h.hexdigest()[:16]
