"""Text normalisation: sentence "beats", name masking, light stemming, synonym folding.

Everything here is deterministic and dependency-light (only scikit-learn's stop-word list).
"""
from __future__ import annotations

import re
from typing import Iterable

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

_ABBREV = ["Mr.", "Mrs.", "Ms.", "Dr.", "St.", "Prof.", "Capt.", "Col."]
_SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z\"'(\[])")
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")

# Words that carry no plot information in this domain, on top of sklearn's list.
_DOMAIN_STOP = {
    "story", "stories", "show", "series", "episode", "year", "years", "day", "days",
    "later", "finally", "soon", "one", "two", "three", "four", "five", "ten", "first",
    "also", "new", "old", "back", "make", "makes", "made", "get", "gets", "got",
}
STOPWORDS = set(ENGLISH_STOP_WORDS) | _DOMAIN_STOP
_HONORIFICS = {"mr", "mrs", "ms", "dr", "prof", "capt", "col", "st"}

# Synonym folding (applied to lower-cased surface forms BEFORE stemming).
# Hand-written, ~90 entries; this is deliberately small and is listed as a limitation.
SYNONYMS = {
    "chauffeur": "driver", "fiancee": "fiance", "betrothal": "engagement", "betrothed": "engaged",
    "girlfriend": "mistress", "boyfriend": "lover", "dad": "father", "mom": "mother", "mum": "mother",
    "grandkids": "grandchildren", "grandchild": "grandchildren", "magnate": "tycoon",
    "billionaire": "tycoon", "ceo": "tycoon", "mogul": "tycoon", "solicitor": "lawyer",
    "attorney": "lawyer", "testament": "will", "journal": "diary", "notebook": "diary",
    "sketchbook": "diary", "cook": "chef", "eatery": "restaurant", "cafe": "restaurant",
    "kebab": "dish", "kebabs": "dish", "biryani": "dish", "ramen": "noodle", "noodles": "noodle",
    "formula": "recipe", "blaze": "fire", "arson": "fire", "arsonist": "fire", "arsonists": "fire",
    "burn": "fire", "burns": "fire", "burned": "fire", "burnt": "fire", "spouse": "husband",
    "maid": "servant", "domestic": "servant", "mop": "scrub", "banished": "exile", "exiled": "exile",
    "banish": "exile", "destined": "fated", "feeble": "weak", "werewolf": "wolf", "werewolves": "wolf",
    "wolves": "wolf", "switched": "swap", "switch": "swap", "swapped": "swap", "swaps": "swap",
    "shanty": "slum", "genetic": "dna", "pleads": "beg", "begs": "beg", "begging": "beg",
    "grovels": "beg", "grovel": "beg", "apologise": "apologize", "stepmom": "stepmother",
    "wed": "marry", "wedded": "marry", "married": "marry", "marriage": "marry", "wife": "wife",
    "tutor": "teacher", "gown": "dress", "palace": "mansion", "villa": "mansion", "manor": "mansion",
    "estate": "mansion", "firm": "company", "business": "company", "group": "company",
    "empire": "company", "shop": "store", "stall": "cart", "paper": "contract", "script": "plot",
    "heiress": "heir", "tycoons": "tycoon", "sister": "sister", "sibling": "sister",
    "abducted": "kidnap", "kidnapped": "kidnap", "abduct": "kidnap", "gangster": "mafia",
    "mob": "mafia", "cop": "detective", "policeman": "detective", "investigators": "police",
    "fundraiser": "gala", "fundraising": "gala", "banquet": "gala", "celebration": "party",
    "ceremony": "ceremony", "disguised": "disguise", "disguises": "disguise", "posing": "pose",
    "poses": "pose", "posed": "pose", "stranger": "stranger", "loans": "debt", "loan": "debt",
    "debts": "debt", "creditors": "debt", "lender": "debt", "reunited": "reunion",
    "motherinlaw": "mother-in-law", "ex-husband": "ex", "ex-fiancee": "ex", "ex-wife": "ex",
}


_CONNECTORS = {"and", "but", "then", "when", "after", "while", "before", "until", "so", "as", "once", "where", "because"}


def _split_long(beat: str, max_words: int = 32, min_chunk: int = 8) -> list[str]:
    """Fallback for unpunctuated / run-on text: break an over-long beat at clause connectors."""
    words = beat.split()
    if len(words) <= max_words:
        return [beat]
    chunks, cur = [], []
    for i, w in enumerate(words):
        if len(cur) >= min_chunk and (w.lower() in _CONNECTORS or len(cur) >= max_words) and len(words) - i >= 4:
            chunks.append(" ".join(cur))
            cur = []
        cur.append(w)
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def split_sentences(text: str) -> list[str]:
    """Split a pitch into ordered "beats". Newlines are treated as hard breaks; run-on text is chunked."""
    beats: list[str] = []
    for line in re.split(r"[\r\n]+", text):
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if not line:
            continue
        t = re.sub(r"\s+", " ", line)
        for a in _ABBREV:
            t = t.replace(a, a.replace(".", "<DOT>"))
        for part in _SENT_SPLIT.split(t):
            part = part.replace("<DOT>", ".").strip()
            if part:
                beats.extend(_split_long(part))
    return beats


def build_known_vocab(texts: Iterable[str]) -> set[str]:
    """Lower-case words seen in non-initial, non-capitalised position (i.e. ordinary words)."""
    vocab: set[str] = set()
    for t in texts:
        for s in split_sentences(t):
            for i, m in enumerate(_WORD.finditer(s)):
                w = m.group(0)
                if i > 0 and not w[0].isupper():
                    vocab.add(w.lower().rstrip("'s"))
    return vocab


def find_names(sentences: list[str], known_vocab: set[str] | None = None) -> set[str]:
    """Heuristic proper-noun finder. A capitalised word is a name if it appears capitalised in the
    MIDDLE of a sentence, or is capitalised in two or more different sentences (names recur; a
    sentence-initial common word like "Billionaire" or "Widow" usually appears once)."""
    mid: set[str] = set()
    init_sentences: dict[str, int] = {}
    for s in sentences:
        seen_here: set[str] = set()
        for i, m in enumerate(_WORD.finditer(s)):
            w = m.group(0)
            if not w[0].isupper() or (len(w) > 1 and w.isupper()):
                continue
            base = re.sub(r"'s$", "", w).lower()
            if base in _HONORIFICS or base in STOPWORDS:
                continue
            if i > 0:
                mid.add(base)
            elif base not in seen_here:
                init_sentences[base] = init_sentences.get(base, 0) + 1
            seen_here.add(base)
    return mid | {w for w, n in init_sentences.items() if n >= 2}


def stem(w: str) -> str:
    if len(w) <= 3:
        return w
    if w.endswith("sses"):
        w = w[:-2]
    elif w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("ied") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("ss") or w.endswith("us") or w.endswith("is"):
        pass
    elif w.endswith("s") and len(w) > 3:
        w = w[:-1]
    if w.endswith("ing") and len(w) > 5:
        w = w[:-3]
        if len(w) > 2 and w[-1] == w[-2] and w[-1] not in "lsz":
            w = w[:-1]
    elif w.endswith("ed") and len(w) > 4:
        w = w[:-2]
        if len(w) > 2 and w[-1] == w[-2] and w[-1] not in "lsz":
            w = w[:-1]
    elif w.endswith("ly") and len(w) > 5:
        w = w[:-2]
    if w.endswith("e") and len(w) > 4:
        w = w[:-1]
    return w


def normalise_tokens(sentence: str, names: set[str]) -> list[str]:
    """Lower-case, drop names and stop-words, fold synonyms, stem."""
    out: list[str] = []
    for m in _WORD.finditer(sentence):
        raw = m.group(0)
        low = re.sub(r"'s$", "", raw.lower())
        if low in names or low in STOPWORDS or len(low) < 3:
            continue
        for piece in low.split("-"):
            if len(piece) < 3 or piece in STOPWORDS:
                continue
            piece = SYNONYMS.get(piece, piece)
            out.append(stem(piece))
    return out
