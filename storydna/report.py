"""Report building, validation and export."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from datetime import datetime, timezone

from . import __version__
from .catalogue import StoryCard, catalogue_fingerprint, clean_pitch
from .matcher import CONFIG, StoryIndex
import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from .textproc import split_sentences
from .suggest import suggest_for_candidate
from .translate import prepare_text

CAVEAT = ("Review priority is an editorial triage signal, not a probability of copying and not a legal "
          "assessment. Ideas and genre tropes are not protectable; only a human reviewer can judge originality.")


def _input_warnings(text: str, beats: list[str], check_language: bool = True) -> list[str]:
    w = []
    if len(beats) < 4:
        w.append("Very short pitch (%d beats): too little plot to compare reliably." % len(beats))
    if not check_language:
        return w
    letters = [c for c in text if c.isalpha()]
    if letters and sum(1 for c in letters if ord(c) < 128) / len(letters) < 0.7:
        w.append("Text is mostly non-English/non-Latin. The event lexicon is English-only, so matching "
                 "falls back to weak lexical overlap. Treat results as unreliable.")
    words = re.findall(r"[a-z']+", text.lower())
    if len(words) >= 12 and sum(x in ENGLISH_STOP_WORDS for x in words) / len(words) < 0.20 and not any("non-English" in x for x in w):
        w.append("The text does not look like English (very few English function words; e.g. Hindi written in Roman "
                 "letters). The lexicon and vocabulary are English-only, so a Low result here is NOT evidence of originality.")
    return w


def _trim_evidence(c: dict) -> dict:
    """Presentation-only: keep evidence that is actually informative. Weak pairs are noise for the reviewer,
    especially under Low-priority candidates (this does not change any score or tier)."""
    keep = [m for m in c["matched_plot_beats"]
            if (m["events"] and not m["generic_trope_only"]) or m["beat_similarity"] >= 0.18]
    if c["review_priority"] == "Low":
        keep = keep[:2]
    c["matched_plot_beats"] = keep[:6]
    c["supporting_excerpt_or_scene_id"] = ["%s#beat%d" % (c["candidate_id"], m["candidate_beat_index"]) for m in keep[:6]]
    return c


def review_pitch(index: StoryIndex, text: str, *, query_id: str = "pitch", title: str = "", top_k: int = 5,
                 adapter=None, llm_top_n: int = 3, redact_input: bool = False, run_label: str = "",
                 translate: str = "auto", translate_with_model: bool = False,
                 suggest: bool = True, suggest_with_model: bool = False, llm_compare: bool | None = None) -> dict:
    """Compare one pitch against the indexed catalogue and return a JSON-serialisable report.

    translate: 'auto' (default) routes non-English pitches through the language layer (storydna.translate);
    'off' disables it (the old English-only behaviour). translate_with_model lets the configured model translate.
    suggest: attach ways to make the pitch less similar to High/Medium candidates (storydna.suggest); suggest_with_model
    additionally asks the configured model for fresh angles. llm_compare=False keeps the model out of the pair-by-pair
    double-check even when an adapter is passed (it is still used for translation / ideas if those are requested).
    """
    text = clean_pitch(text)
    prep = prepare_text(text, adapter if translate_with_model else None, mode=translate)
    translated = prep.method in ("glossary", "llm") and bool(split_sentences(prep.working_en))
    working = prep.working_en if translated else text
    q, top, _all, _ = index.score(working, top_k=top_k, query_id=query_id)
    candidates = []
    for rank, res in enumerate(top, start=1):
        c = _trim_evidence(index.explain(q, res))
        c["rank"] = rank
        card = index.by_id[c["candidate_id"]]
        for m in c["matched_plot_beats"]:
            if translated:
                k = prep.beat_src[m["pitch_beat_index"]] if m["pitch_beat_index"] < len(prep.beat_src) else None
                if k is not None:
                    m["pitch_text_original"] = prep.native_sentences[k]
            if card.beats_original and m["candidate_beat_index"] < len(card.beats_original):
                m["candidate_text_original"] = card.beats_original[m["candidate_beat_index"]]
        if prep.method == "unsupported":
            # An English-only matcher looking at, say, Spanish text produces meaningless rankings; do not present them.
            c.update(review_priority="Not assessed", matched_plot_beats=[], differentiating_beats=[], supporting_excerpt_or_scene_id=[],
                     shared_distinctive_events=[], shared_generic_tropes=[],
                     recommendation="Not assessed: the pitch language is not supported without a model (see warnings).")
        candidates.append(c)
    if suggest and prep.method != "unsupported":
        for c in [c for c in candidates if c["review_priority"] in ("High", "Medium")][:3]:
            c["differentiation"] = suggest_for_candidate(index, c, working, adapter if suggest_with_model else None)
    llm_info = {"adapter": "none"}
    if adapter is not None and getattr(adapter, "name", "none") != "none" and llm_compare is not False:
        from .llm import llm_compare as _llm_compare
        llm_info = {"adapter": adapter.name}
        for c in (candidates[:llm_top_n] if prep.method != "unsupported" else []):
            cand_card = index.by_id[c["candidate_id"]]
            c["llm_review"] = _llm_compare(q.beats, cand_card.beats, adapter)
            v = c["llm_review"].get("verdict")
            if v == "shared_tropes_only" and c["review_priority"] == "High":
                c["failure_notes"] = "Model and heuristic disagree: heuristic High, model says tropes only. Human check."
            elif v == "same_plot" and c["review_priority"] == "Low":
                c["failure_notes"] = "Model and heuristic disagree: heuristic Low, model says same plot. Human check."
    now = datetime.now(timezone.utc)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    report = {
        "run_id": "%s_%s" % (now.strftime("%Y%m%dT%H%M%SZ"), sha[:8]),
        "run_label": run_label,
        "created_utc": now.isoformat(timespec="seconds"),
        "storydna_version": __version__,
        "catalogue": {"n_cards": index.n, "fingerprint": catalogue_fingerprint(index.cards)},
        "config": {
            "scoring": "calibrated logistic combination (calibration.json)" if index.calib else "fallback fixed weights",
            "tiers": index.calib["tiers"] if index.calib else {"high": index.cfg["high"], "medium": index.cfg["medium"]},
            "calibration_fit_on": index.calib["fit_on"] if index.calib else None,
            "generic_event_df": index.cfg["generic_event_df"], "rare_token_df": index.cfg["rare_token_df"],
        },
        "llm": llm_info,
        "query_id": query_id, "source_title": title or query_id,
        "input_sha256": sha, "input_text": None if redact_input else text,
        "working_text_en": working if (translated and not redact_input) else None,
        "language": {
            "detected": prep.language["code"], "name": prep.language["name"], "script": prep.language["script"],
            "confidence": prep.language["confidence"], "evidence": prep.language["evidence"],
            "method": prep.method if translated or prep.method == "unsupported" else "none",
            "reliable": prep.reliable if (translated or prep.method == "unsupported") else True,
            "recognised_share": prep.recognised_share, "unrecognised_sample": prep.unrecognised,
        },
        "input_beats": len(q.beats),
        "input_warnings": _input_warnings(working, q.beats,
                                          check_language=not translated and prep.method != "unsupported") + prep.warnings,
        "caveat": CAVEAT,
        "top_candidates": candidates,
    }
    problems = validate_report(report, index)
    report["validation"] = {"ok": not problems, "problems": problems}
    return report


def validate_report(report: dict, index: StoryIndex) -> list[str]:
    """Structural checks from the brief: real IDs, unique ranks, finite scores, grounded evidence, JSON-safe."""
    problems: list[str] = []
    cands = report.get("top_candidates", [])
    if not cands:
        problems.append("no candidates returned")
    ranks = [c.get("rank") for c in cands]
    if len(set(ranks)) != len(ranks):
        problems.append("duplicate ranks")
    ids = [c.get("candidate_id") for c in cands]
    if len(set(ids)) != len(ids):
        problems.append("duplicate candidate ids")
    src = report.get("working_text_en") or report.get("input_text")
    qbeats = split_sentences(src) if src else None
    for c in cands:
        cid = c.get("candidate_id")
        if cid not in index.by_id:
            problems.append("candidate %r not in catalogue" % cid)
            continue
        s = c.get("retrieval_score")
        if not isinstance(s, (int, float)) or not math.isfinite(s):
            problems.append("non-finite score for %s" % cid)
        cb = index.by_id[cid].beats
        for m in c.get("matched_plot_beats", []):
            j = m["candidate_beat_index"]
            if not (0 <= j < len(cb)) or cb[j] != m["candidate_text"]:
                problems.append("evidence for %s does not match catalogue text (beat %s)" % (cid, j))
            if qbeats is not None:
                i = m["pitch_beat_index"]
                if not (0 <= i < len(qbeats)) or qbeats[i] != m["pitch_text"]:
                    problems.append("evidence for %s does not match pitch text (beat %s)" % (cid, i))
    try:
        json.dumps(report)
    except (TypeError, ValueError) as e:
        problems.append("report is not JSON-serialisable: %s" % e)
    return problems


def report_to_csv(report: dict) -> str:
    buf = io.StringIO()
    cols = ["query_id", "rank", "candidate_id", "candidate_title", "review_priority", "retrieval_score",
            "ordered_event_overlap", "lexical_cosine", "rare_detail_overlap", "n_matched_beats",
            "shared_distinctive_events", "shared_generic_tropes", "reviewer_decision", "failure_notes"]
    w = csv.writer(buf)
    w.writerow(cols)
    for c in report["top_candidates"]:
        cm = c["components"]
        w.writerow([report["query_id"], c["rank"], c["candidate_id"], c["candidate_title"], c["review_priority"],
                    c["retrieval_score"], cm["ordered_event_overlap"], cm["lexical_cosine"],
                    cm["rare_detail_overlap"], len(c["matched_plot_beats"]),
                    ";".join(c["shared_distinctive_events"]), ";".join(c["shared_generic_tropes"]),
                    c.get("reviewer_decision") or "", c.get("failure_notes", "")])
    return buf.getvalue()


def report_to_markdown(report: dict) -> str:
    L = ["# StoryDNA review: %s" % report["source_title"], "",
         "_%s_" % report["caveat"], ""]
    lg = report.get("language") or {}
    if lg.get("method") in ("glossary", "llm"):
        L.append("_Language: %s -> compared as English via %s%s._" % (lg["name"], lg["method"], "" if lg.get("reliable", True) else " (low reliability)"))
    for w in report["input_warnings"]:
        L.append("> WARNING: %s" % w)
    if (report.get("language") or {}).get("method") == "unsupported":
        L += ["", "**No comparison was made** (language not supported without a model). Provide an English synopsis or enable "
                  "model translation."]
        return "\n".join(L)
    for c in report["top_candidates"]:
        L += ["", "## #%d  %s (%s) - **%s** (score %.2f)" % (c["rank"], c["candidate_title"], c["candidate_id"],
                                                          c["review_priority"], c["retrieval_score"]),
              "Distinctive shared events: %s | generic tropes shared: %s" % (
                  ", ".join(c["shared_distinctive_events"]) or "none", ", ".join(c["shared_generic_tropes"]) or "none")]
        for m in c["matched_plot_beats"][:6]:
            L.append("- [%s] pitch: \"%s\"  <->  catalogue: \"%s\"" % ("/".join(m["events"]), m["pitch_text"],
                                                                     m["candidate_text"]))
            if m.get("pitch_text_original"):
                L.append("    (original pitch sentence: \"%s\")" % m["pitch_text_original"])
        for d in c["differentiating_beats"]:
            L.append("- differs (%s): \"%s\"" % (d["side"], d["text"]))
        df = c.get("differentiation")
        if df:
            L += ["", "**How to make this pitch more original** - %s" % df["headline"]]
            pv = df.get("rewrite_preview") or {}
            if pv.get("after"):
                L.append("- What-if: rewriting beat(s) %s moves the score %.2f (%s) -> %.2f (%s)." % (
                    ", ".join(str(i + 1) for i in pv["beats_to_rewrite"]), pv["before"]["score"], pv["before"]["tier"],
                    pv["after"]["score"], pv["after"]["tier"]))
            for f in df["beat_fixes"]:
                L.append("- Beat %d (\"%s\") mirrors \"%s\"" % (f["pitch_beat_index"] + 1, f["pitch_text"], f["mirrors"]))
                for i in f["ideas"]:
                    L.append("    - %s" % i["idea"])
            for a in df["angles"]:
                L.append("- %s: %s" % (a["title"], a["idea"]))
            for i in ((df.get("model_ideas") or {}).get("ideas") or []):
                L.append("- Model idea: %s" % i["idea"])
        L.append("- Recommendation: %s" % c["recommendation"])
    return "\n".join(L)
