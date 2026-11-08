"""Language layer: make a non-English pitch/catalogue comparable by the English matcher.

Routes (see `prepare_text`):
  * English                  -> unchanged.
  * Hindi (Devanagari) or Roman-script Hindi ("Hinglish")
                             -> offline glossary gloss (storydna.glossary_hi): approximate, covers common
                                melodrama vocabulary only, reports what it could not read.
  * any language + a model   -> the swappable LLM translates sentence by sentence; the answer is validated
                                (same number of sentences, non-empty, not wildly longer) or discarded.
  * any other language, no model -> NOT scored reliably; the report says so (language.reliable = false).

The scorer itself (matcher/events/textproc) is untouched and still sees English only.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .glossary_hi import DEVANAGARI, MAX_PHRASE, ROMAN, _norm_dev, rkey
from .lang import detect_language
from .textproc import split_sentences

_DEV = "ऀ-ॣ०-ॿ‌‍"
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-]*|[" + _DEV + r"]+|[,;:]")
_NATIVE_SPLIT = re.compile(r"(?<=[.!?।॥])\s+|\n+|(?<=[।॥])")
GLOSSARY_LANGS = {"hi", "hi-Latn"}


class TranslationError(RuntimeError):
    pass


@dataclass
class Prepared:
    original: str
    working_en: str
    language: dict
    method: str                                  # none | glossary | llm | unsupported
    native_sentences: list[str] = field(default_factory=list)
    beat_src: list[int] = field(default_factory=list)      # English beat k came from native_sentences[beat_src[k]]
    warnings: list[str] = field(default_factory=list)
    reliable: bool = True
    unrecognised: list[str] = field(default_factory=list)
    recognised_share: float | None = None


# ----------------------------------------------------------------------------------------- helpers
def split_native(text: str) -> list[str]:
    out = []
    for line in re.split(r"[\r\n]+", text):
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        out += [p.strip() for p in _NATIVE_SPLIT.split(line) if p and p.strip(" ।॥.!?")]
    return out


_C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
      "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
      "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
      "ष": "sh", "स": "s", "ह": "h", "ळ": "l"}
_V = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o",
      "औ": "au", "ऑ": "o", "ऍ": "e"}
_M = {"ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
      "ॉ": "o", "ॅ": "e"}


def transliterate(word: str) -> str:
    """Rough Devanagari -> Latin (so unknown words, mostly names, survive as capitalised tokens)."""
    out, i = [], 0
    w = word.replace("़", "")
    while i < len(w):
        c = w[i]
        if c in _C:
            nxt = w[i + 1] if i + 1 < len(w) else ""
            if nxt == "्":
                out.append(_C[c]); i += 2; continue
            out.append(_C[c])
            if nxt in _M:
                out.append(_M[nxt]); i += 2; continue
            if i + 1 < len(w):          # inherent 'a' (dropped at word end)
                out.append("a")
        elif c in _V:
            out.append(_V[c])
        elif c in ("ं", "ँ"):
            out.append("n")
        elif c == "ः":
            out.append("h")
        i += 1
    s = "".join(out)
    return s.capitalize() if s else ""


def _gloss_sentence(sent: str, stats: dict) -> str:
    sent = re.sub(r"(?<=[" + _DEV + r"])-(?=[" + _DEV + r"])", " ", sent)
    toks = _TOKEN.findall(sent)
    clauses: list[list[tuple[str, str]]] = [[]]
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in ",;:":
            clauses.append([])
            i += 1
            continue
        is_dev = "ऀ" <= t[0] <= "ॿ"
        table = DEVANAGARI if is_dev else ROMAN
        keyf = _norm_dev if is_dev else rkey
        hit = None
        for n in range(min(MAX_PHRASE, len(toks) - i), 0, -1):
            span = toks[i:i + n]
            if any(x in ",;:" for x in span):
                continue
            if is_dev != ("ऀ" <= span[0][0] <= "ॿ") or any(("ऀ" <= x[0] <= "ॿ") != is_dev for x in span):
                continue
            key = tuple(keyf(x) for x in span)
            if key in table:
                hit = (table[key], n)
                break
        if hit:
            (eng, kind), n = hit
            if kind != "f" and eng:
                clauses[-1].append((eng, kind))
                stats["recognised"] += 1
            i += n
            continue
        if is_dev:
            tr = transliterate(t)
            if tr:
                clauses[-1].append((tr, "n"))
            stats["unknown_dev"] += 1
            stats["unrec"].append(t)
        else:
            clauses[-1].append((t, "n"))
            if t[0].islower() and not t.isdigit():
                stats["unknown_roman"] += 1
                stats["unrec"].append(t)
        i += 1
    parts = []
    for cl in clauses:
        if not cl:
            continue
        verbs = [e for e, k in cl if k == "v"]
        rest = [e for e, k in cl if k != "v"]
        if verbs and rest:
            ordered = rest[:1] + verbs + rest[1:]
        else:
            ordered = verbs + rest
        parts.append(" ".join(ordered))
    s = ", ".join(parts).strip(" ,")
    return (s[0].upper() + s[1:] + ".") if s else ""


def gloss_text(sentences: list[str]) -> tuple[list[str], dict]:
    stats = {"recognised": 0, "unknown_dev": 0, "unknown_roman": 0, "unrec": []}
    out = [_gloss_sentence(s, stats) for s in sentences]
    return out, stats


# ----------------------------------------------------------------------------------------- LLM
def llm_translate(sentences: list[str], language_name: str, adapter) -> list[str]:
    from .llm import _load_prompt, _parse_json, AdapterError   # local import: llm imports textproc only
    system, user_t = _load_prompt("translate_beats.txt")
    numbered = "\n".join("%d. %s" % (i + 1, s) for i, s in enumerate(sentences))
    user = user_t.replace("{language}", language_name).replace("{sentences}", numbered)
    last = "unknown"
    for _ in range(2):
        try:
            raw = adapter.complete(system, user, max_tokens=2500)
            out = _parse_json(raw).get("sentences")
        except AdapterError as e:
            raise TranslationError(str(e))
        except (ValueError, json.JSONDecodeError) as e:
            last = "unparseable model output (%s)" % e
            continue
        if not isinstance(out, list) or len(out) != len(sentences):
            last = "model returned %s sentences, expected %d" % (len(out) if isinstance(out, list) else "no", len(sentences))
            continue
        out = [str(x).strip() for x in out]
        bad = [i for i, (a, b) in enumerate(zip(sentences, out)) if not b or len(b.split()) > 6 * max(len(a.split()), 3) + 12]
        if bad:
            last = "empty or implausibly long translation for sentence(s) %s" % [i + 1 for i in bad]
            continue
        return [x if x[-1] in ".!?" else x + "." for x in out]
    raise TranslationError(last)


# ----------------------------------------------------------------------------------------- public
def prepare_text(text: str, adapter=None, *, mode: str = "auto") -> Prepared:
    """mode: 'auto' (glossary for Hindi/Hinglish, model for others if `adapter` is given), 'glossary', 'llm', 'off'."""
    lang = detect_language(text)
    code = lang["code"]
    base = Prepared(original=text, working_en=text, language=lang, method="none")
    if mode == "off" or code == "en":
        return base
    have_model = adapter is not None and getattr(adapter, "name", "none") != "none"
    sentences = split_native(text)
    if not sentences:
        return base
    use_llm = have_model and mode in ("auto", "llm")
    if use_llm:
        try:
            en = llm_translate(sentences, lang["name"], adapter)
            return _finish(base, sentences, en, "llm",
                           ["Translated by %s; the matcher compares the English translation." % adapter.name])
        except TranslationError as e:
            base.warnings.append("Model translation failed (%s); " % e + (
                "falling back to the offline glossary." if code in GLOSSARY_LANGS else "pitch not translated."))
    if code in GLOSSARY_LANGS and mode in ("auto", "glossary", "llm"):
        en, st = gloss_text(sentences)
        n_dev_total = st["recognised"] + st["unknown_dev"] + st["unknown_roman"]
        base.recognised_share = round(st["recognised"] / n_dev_total, 3) if n_dev_total else None
        base.unrecognised = sorted(set(st["unrec"]))[:12]
        notes = ["Hindi text was converted to English with a small offline glossary (approximate; a model gives better "
                 "results: set STORYDNA_PROVIDER/MODEL/KEY and tick 'translate with model')."]
        if code == "hi" and st["unknown_dev"] > 0.4 * max(1, st["recognised"] + st["unknown_dev"]):
            notes.append("More than 40%% of the Devanagari words are not in the glossary (e.g. %s). Treat a Low result as "
                         "unreliable." % ", ".join(base.unrecognised[:5]))
            base.reliable = False
        return _finish(base, sentences, en, "glossary", notes)
    base.method = "unsupported"
    base.reliable = False
    base.warnings.append("%s is not supported without a model: the matcher reads English only, so a Low result here is NOT "
                         "evidence of originality. Configure a model (STORYDNA_PROVIDER / STORYDNA_MODEL / STORYDNA_API_KEY) "
                         "and enable 'translate with model', or supply an English synopsis." % lang["name"])
    return base


def _finish(prep: Prepared, native: list[str], en: list[str], method: str, notes: list[str]) -> Prepared:
    lines, src = [], []
    for k, e in enumerate(en):
        parts = split_sentences(e) or ([e] if e.strip() else [])
        for p in parts:
            lines.append(p)
            src.append(k)
    prep.native_sentences = native
    prep.working_en = "\n".join(lines)
    prep.beat_src = src
    prep.method = method
    prep.warnings += notes
    if not prep.working_en.strip():
        prep.reliable = False
        prep.warnings.append("Nothing could be read from this text.")
    return prep


def prepare_catalogue(cards, adapter=None, *, mode: str = "auto"):
    """Return cards whose synopses are English-comparable (non-English cards translated; originals kept)."""
    from dataclasses import replace
    out, notes = [], []
    for c in cards:
        if mode == "off":
            out.append(c)
            continue
        declared = (c.language or "en").lower()
        prep = None
        if declared not in ("en", "eng", "english") or detect_language(c.synopsis)["code"] != "en":
            prep = prepare_text(c.synopsis, adapter, mode=mode)
        if prep is None or prep.method in ("none",):
            out.append(c)
            continue
        if prep.method == "unsupported":
            notes.append("%s: language not supported without a model; left untranslated" % c.story_id)
            out.append(c)
            continue
        beats_en, beats_src = [], []
        for line_idx, line in enumerate(prep.working_en.split("\n")):
            beats_en.append(line)
        out.append(replace(c, synopsis=prep.working_en.replace("\n", " "), original_synopsis=c.synopsis, beats=beats_en,
                           beats_original=[prep.native_sentences[k] for k in prep.beat_src]))
    return out, notes
