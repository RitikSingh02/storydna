"""StoryDNA matcher: retrieval + ordered plot-event comparison + explainable review tiers.

Stage 1 (retrieval): TF-IDF over normalised tokens (names removed, stemmed, synonyms folded).
Stage 2 (structure): each beat is tagged with story events; the ORDERED event sequences of the
pitch and each candidate are aligned with a rarity-weighted longest-common-subsequence. Events
that are common across the catalogue ("humiliation", "public reveal") carry little weight, so two
stories only score high when they share a chain of *distinctive* events in the same order AND
reuse distinctive concrete details.

The score is an editorial review priority, NOT a probability of copying or a legal finding.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from . import __version__
from .catalogue import StoryCard
from .events import EVENT_LABELS, tag_beat
from .textproc import build_known_vocab, find_names, normalise_tokens, split_sentences

# --- thresholds & weights: design hypotheses, calibrated on the dev benchmark (see docs) -------
CONFIG = {
    "weights": {"ordered": 0.40, "lexical": 0.30, "rare_detail": 0.20, "event_set": 0.10},
    "generic_event_df": 0.25,      # an event present in >= 25% of catalogue stories is "generic" (trope-like)
    "rare_token_df": 2,            # a token appearing in <= 2 catalogue stories is a "distinctive detail"
    "high": {"min_matched": 3, "min_distinct_matched": 2, "min_ordered": 0.50, "min_rare": 0.12, "min_lex": 0.25},
    "medium": {"min_lex": 0.20, "min_rare": 0.15, "min_ordered": 0.50, "min_distinct_for_ordered": 3,
               "min_detail_with_ordered": 0.10},
    "prefilter_k": 50,
    "top_k": 5,
}


CALIBRATION_PATH = Path(__file__).parent / "calibration.json"


def load_calibration(path: Path | None = None) -> dict | None:
    p = path or CALIBRATION_PATH
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    d["mu"], d["sd"], d["coef"] = np.array(d["mu"]), np.array(d["sd"]), np.array(d["coef"])
    return d


@dataclass
class Analysis:
    beats: list[str]
    tokens: list[list[str]]
    events: list[tuple[str, int]]          # (label, beat_index) in story order
    token_set: set[str] = field(default_factory=set)

    @property
    def event_set(self) -> set[str]:
        return {e for e, _ in self.events}


def analyse(beats: list[str], known_vocab: set[str], extra_names: set[str] | None = None) -> Analysis:
    names = find_names(beats, known_vocab) | (extra_names or set())
    toks = [normalise_tokens(b, names) for b in beats]
    events: list[tuple[str, int]] = []
    for i, b in enumerate(beats):
        for lbl in tag_beat(b):
            events.append((lbl, i))
    return Analysis(beats=beats, tokens=toks, events=events, token_set={t for ts in toks for t in ts})


def _doc_tokens(an: Analysis) -> list[str]:
    out: list[str] = []
    for ts in an.tokens:
        out.extend(ts)
        out.extend("%s_%s" % (a, b) for a, b in zip(ts, ts[1:]))
    return out


def weighted_lcs(a: list[tuple[str, int]], b: list[tuple[str, int]], w: dict[str, float]):
    """Weighted LCS over event labels. Returns (score, [(i, j), ...]) with indices into a and b."""
    n, m = len(a), len(b)
    dp = np.zeros((n + 1, m + 1))
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1][0] == b[j - 1][0]:
                dp[i, j] = dp[i - 1, j - 1] + w.get(a[i - 1][0], 0.1)
            else:
                dp[i, j] = max(dp[i - 1, j], dp[i, j - 1])
    i, j, pairs = n, m, []
    while i > 0 and j > 0:
        if a[i - 1][0] == b[j - 1][0] and abs(dp[i, j] - (dp[i - 1, j - 1] + w.get(a[i - 1][0], 0.1))) < 1e-12:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif dp[i - 1, j] >= dp[i, j - 1]:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return float(dp[n, m]), pairs


def beat_alignment(q: "Analysis", c: "Analysis", idf: dict[str, float], tau: float = 0.12):
    """Lexicon-free ordered alignment of beats. sim(i,j) is an IDF-weighted overlap of normalised
    tokens (unknown tokens ignored so heavy paraphrase is not double-punished). A monotonic DP picks
    the best in-order set of beat pairs with sim >= tau. Returns (score in [0,1], pairs)."""
    def vec(ts):
        return {t: idf[t] for t in set(ts) if t in idf}
    qv, cv = [vec(ts) for ts in q.tokens], [vec(ts) for ts in c.tokens]
    qn = [math.sqrt(sum(v * v for v in d.values())) for d in qv]
    cn = [math.sqrt(sum(v * v for v in d.values())) for d in cv]
    n, m = len(qv), len(cv)
    S = np.zeros((n, m))
    for i in range(n):
        for j in range(m):
            if qn[i] and cn[j]:
                S[i, j] = sum(qv[i][t] * cv[j][t] for t in qv[i].keys() & cv[j].keys()) / (qn[i] * cn[j])
    dp = np.zeros((n + 1, m + 1))
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            take = dp[i - 1, j - 1] + S[i - 1, j - 1] if S[i - 1, j - 1] >= tau else -1
            dp[i, j] = max(dp[i - 1, j], dp[i, j - 1], take)
    i, j, pairs = n, m, []
    while i > 0 and j > 0:
        if S[i - 1, j - 1] >= tau and abs(dp[i, j] - (dp[i - 1, j - 1] + S[i - 1, j - 1])) < 1e-12:
            pairs.append((i - 1, j - 1, float(S[i - 1, j - 1])))
            i -= 1
            j -= 1
        elif dp[i - 1, j] >= dp[i, j - 1]:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    denom = max(n, m)
    return (float(dp[n, m]) / denom if denom else 0.0), pairs


class StoryIndex:
    """Pre-computed index over a catalogue. Build once, query many times."""

    def __init__(self, cards: list[StoryCard], config: dict | None = None):
        if not cards:
            raise ValueError("empty catalogue")
        self.cfg = config or CONFIG
        self.calib = load_calibration() if self.cfg is CONFIG else None
        self.cards = cards
        self.by_id = {c.story_id: c for c in cards}
        self.known_vocab = build_known_vocab([c.synopsis for c in cards])
        self.analyses = [analyse(c.beats, self.known_vocab) for c in cards]
        self.catalogue_names = set()
        for c in cards:
            self.catalogue_names |= find_names(c.beats, self.known_vocab)
        n = len(cards)
        self.n = n
        # token / event document frequencies over the catalogue
        self.tok_df: dict[str, int] = {}
        for an in self.analyses:
            for t in an.token_set:
                self.tok_df[t] = self.tok_df.get(t, 0) + 1
        ev_df = {e: 0 for e in EVENT_LABELS}
        for an in self.analyses:
            for e in an.event_set:
                ev_df[e] += 1
        self.ev_df = ev_df
        self.ev_weight = {
            e: float(np.clip(math.log((n + 1) / (df + 0.5)) / math.log(n + 1), 0.05, 1.0)) for e, df in ev_df.items()
        }
        self.generic_events = {e for e, df in ev_df.items() if df / n >= self.cfg["generic_event_df"]}
        self.idf = {t: math.log((n + 1) / (df + 1)) + 1 for t, df in self.tok_df.items()}
        # lexical models
        self.vec = TfidfVectorizer(analyzer=lambda d: d, sublinear_tf=True)
        self.mat = self.vec.fit_transform([_doc_tokens(a) for a in self.analyses])
        self.plain_vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
        self.plain_mat = self.plain_vec.fit_transform([c.synopsis for c in cards])

    # ---- scoring ---------------------------------------------------------------------------
    def score(self, pitch_text: str, top_k: int | None = None, query_id: str = "query"):
        cfg = self.cfg
        beats = split_sentences(pitch_text)
        q = analyse(beats, self.known_vocab, self.catalogue_names)
        qv = self.vec.transform([_doc_tokens(q)])
        lex = (self.mat @ qv.T).toarray().ravel()
        plain = (self.plain_mat @ self.plain_vec.transform([pitch_text]).T).toarray().ravel()
        order = np.argsort(-lex)
        k = cfg["prefilter_k"] if self.n > cfg["prefilter_k"] else self.n
        shortlist = order[:k]
        wq = sum(self.ev_weight[e] for e, _ in q.events)
        results = []
        for idx in shortlist:
            cand = self.analyses[idx]
            wc = sum(self.ev_weight[e] for e, _ in cand.events)
            lcs, pairs = weighted_lcs(q.events, cand.events, self.ev_weight)
            ordered = (2 * lcs / (wq + wc)) if (wq + wc) > 0 else 0.0
            qs, cs = q.event_set, cand.event_set
            inter = sum(self.ev_weight[e] for e in qs & cs)
            union = sum(self.ev_weight[e] for e in qs | cs)
            event_set = inter / union if union else 0.0
            cand_rare = {t for t in cand.token_set if self.tok_df.get(t, 0) <= cfg["rare_token_df"]}
            shared_rare = sorted(cand_rare & q.token_set)
            rare = len(shared_rare) / len(cand_rare) if cand_rare else 0.0
            matched_events = [e for e, _ in (q.events[i] for i, _ in pairs)]
            distinct_matched = [e for e in matched_events if e not in self.generic_events]
            balign, bpairs = beat_alignment(q, cand, self.idf)
            comps = {
                "beat_alignment": round(balign, 4),
                "ordered_event_overlap": round(ordered, 4),
                "lexical_cosine": round(float(lex[idx]), 4),
                "rare_detail_overlap": round(rare, 4),
                "event_set_overlap": round(event_set, 4),
                "plain_tfidf_cosine": round(float(plain[idx]), 4),
            }
            w = cfg["weights"]
            if self.calib:
                x = np.array([comps[f] for f in self.calib["features"]])
                z = float(((x - self.calib["mu"]) / self.calib["sd"]) @ self.calib["coef"] + self.calib["intercept"])
                review_score = 1 / (1 + math.exp(-z))
                tier = ("High" if review_score >= self.calib["tiers"]["high"]
                        else "Medium" if review_score >= self.calib["tiers"]["medium"] else "Low")
            else:  # fallback: hand-set weights + rule tiers (used when no calibration file exists)
                review_score = (w["ordered"] * ordered + w["lexical"] * min(1.0, float(lex[idx]))
                                + w["rare_detail"] * rare + w["event_set"] * event_set)
                tier = self._tier(comps, len(matched_events), len(distinct_matched))
            results.append({
                "idx": int(idx), "review_score": round(float(review_score), 4), "tier": tier,
                "components": comps, "pairs": pairs, "beat_pairs": bpairs, "shared_rare_tokens": shared_rare[:12],
                "n_matched_events": len(matched_events), "n_distinct_matched_events": len(distinct_matched),
            })
        results.sort(key=lambda r: -r["review_score"])
        top_k = top_k or cfg["top_k"]
        return q, results[:top_k], results, {"plain_order": [int(i) for i in np.argsort(-plain)]}

    def _tier(self, c: dict, n_matched: int, n_distinct: int) -> str:
        h, m = self.cfg["high"], self.cfg["medium"]
        if (n_matched >= h["min_matched"] and n_distinct >= h["min_distinct_matched"]
                and c["ordered_event_overlap"] >= h["min_ordered"]
                and (c["rare_detail_overlap"] >= h["min_rare"] or c["lexical_cosine"] >= h["min_lex"])):
            return "High"
        if (c["lexical_cosine"] >= m["min_lex"] or c["rare_detail_overlap"] >= m["min_rare"]
                or (c["ordered_event_overlap"] >= m["min_ordered"] and n_distinct >= m["min_distinct_for_ordered"]
                    and max(c["lexical_cosine"], c["rare_detail_overlap"]) >= m["min_detail_with_ordered"])):
            return "Medium"
        return "Low"

    # ---- report ----------------------------------------------------------------------------
    def explain(self, q: Analysis, res: dict) -> dict:
        cand = self.analyses[res["idx"]]
        card = self.cards[res["idx"]]
        matched, used_q, used_c = [], set(), set()
        grouped: dict[tuple[int, int], list[str]] = {}
        for i, j in res["pairs"]:
            (lbl, qb), (_, cb) = q.events[i], cand.events[j]
            grouped.setdefault((qb, cb), []).append(lbl)
        sims = {(i, j): s for i, j, s in res.get("beat_pairs", [])}
        for (i, j) in sims:
            grouped.setdefault((i, j), [])
        for (qb, cb), lbls in sorted(grouped.items()):
            used_q.add(qb)
            used_c.add(cb)
            matched.append({
                "events": lbls,
                "generic_trope_only": bool(lbls) and all(l in self.generic_events for l in lbls),
                "beat_similarity": round(sims.get((qb, cb), 0.0), 3),
                "pitch_beat_index": qb, "pitch_text": q.beats[qb],
                "candidate_beat_index": cb, "candidate_text": cand.beats[cb],
            })

        def leftovers(an: Analysis, used: set[int], who: str):
            scored = []
            for bi, toks in enumerate(an.tokens):
                if bi in used:
                    continue
                rare = sum(1 for t in set(toks) if self.tok_df.get(t, 0) <= 2)
                evs = [e for e, b in an.events if b == bi and e not in self.generic_events]
                scored.append((rare + 2 * len(evs), bi))
            scored.sort(reverse=True)
            return [{"side": who, "beat_index": bi, "text": an.beats[bi]} for s, bi in scored[:2] if s > 0]

        diffs = leftovers(q, used_q, "pitch") + leftovers(cand, used_c, "candidate")
        shared_events = sorted({e for e, _ in q.events} & {e for e, _ in cand.events})
        return {
            "candidate_id": card.story_id, "candidate_title": card.title, "source_url": card.source_url or "n/a",
            "candidate_provenance": card.provenance, "candidate_input_granularity": card.granularity,
            "retrieval_score": res["review_score"], "review_priority": res["tier"],
            "components": res["components"],
            "matched_plot_beats": matched,
            "shared_generic_tropes": [e for e in shared_events if e in self.generic_events],
            "shared_distinctive_events": [e for e in shared_events if e not in self.generic_events],
            "shared_rare_details": res["shared_rare_tokens"],
            "differentiating_beats": diffs,
            "supporting_excerpt_or_scene_id": [
                "%s#beat%d" % (card.story_id, m["candidate_beat_index"]) for m in matched
            ],
            "recommendation": _recommendation(res["tier"]),
            "reviewer_decision": None, "failure_notes": "",
        }


def _recommendation(tier: str) -> str:
    return {
        "High": "Compare full outlines before approving. Several distinctive events recur in the same order "
                "with shared concrete details. This is an editorial review flag, not a plagiarism finding.",
        "Medium": "Premise or some events overlap; check the differing beats and decide whether the "
                  "difference is strong enough.",
        "Low": "Overlap is mostly genre / vocabulary. No action suggested.",
    }[tier]
