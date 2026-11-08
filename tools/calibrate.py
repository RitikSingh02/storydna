#!/usr/bin/env python3
"""Fit the review-score weights on the DEV queries and estimate generalisation with
leave-one-query-out (LOQO) cross-validation.

Dev = round-1 benchmark (40) + round-3 fresh set (14) = 54 pitches. A separate round-4 set (never used here)
is the final test. Writes storydna/calibration.json when run with --write.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from storydna.catalogue import load_catalogue  # noqa: E402
from storydna.matcher import StoryIndex  # noqa: E402

FEATS = ["plain_tfidf_cosine", "lexical_cosine", "rare_detail_overlap", "ordered_event_overlap",
         "event_set_overlap", "beat_alignment"]


def load_cases(cards, files):
    cases = []
    by_id = {c.story_id: c for c in cards}
    for f in files:
        spec = json.loads(Path(f).read_text())
        for sid in spec.get("exact_ids", []):
            t = re.sub(r"[^\w\s]", "", by_id[sid].synopsis.lower())
            cases.append({"qid": "E_" + sid, "category": "EXACT", "relevant": [sid], "text": re.sub(r"\s+", " ", t)})
        cases += spec["queries"]
    return cases


def featurise(ix, cases):
    rows = []  # per query: dict(qid, category, relevant, ids, X)
    for c in cases:
        q, _top, allr, _ = ix.score(c["text"], top_k=5)
        ids = [ix.cards[r["idx"]].story_id for r in allr]
        X = np.array([[r["components"][f] for f in FEATS] for r in allr])
        rows.append({"qid": c["qid"], "category": c["category"], "relevant": c["relevant"], "ids": ids, "X": X})
    return rows


def fit(rows, C=1.0, exact_weight=0.3):
    X, y, w = [], [], []
    for r in rows:
        for k, sid in enumerate(r["ids"]):
            X.append(r["X"][k])
            y.append(1 if sid in r["relevant"] else 0)
            w.append(exact_weight if r["category"] == "EXACT" else 1.0)
    X, y, w = np.array(X), np.array(y), np.array(w)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    lr = LogisticRegression(C=C, class_weight="balanced", max_iter=2000)
    lr.fit((X - mu) / sd, y, sample_weight=w)
    return {"mu": mu, "sd": sd, "coef": lr.coef_[0], "intercept": float(lr.intercept_[0])}


def predict(model, X):
    z = ((X - model["mu"]) / model["sd"]) @ model["coef"] + model["intercept"]
    return 1 / (1 + np.exp(-z))


def top1(rows, scorefn):
    out = []
    for r in rows:
        s = scorefn(r)
        k = int(np.argmax(s))
        out.append((r, float(s[k]), r["ids"][k]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--C", type=float, default=1.0)
    a = ap.parse_args()
    cards = load_catalogue(ROOT / "data/catalogue.json")
    ix = StoryIndex(cards)
    files = [ROOT / "data/benchmark/queries.json", ROOT / "data/benchmark/queries_round3_fresh.json"]
    rows = featurise(ix, load_cases(cards, files))
    print("dev queries:", len(rows))

    # LOQO cross-validation
    cv_scores = []
    for i, r in enumerate(rows):
        m = fit(rows[:i] + rows[i + 1:], C=a.C)
        cv_scores.append(predict(m, r["X"]))

    def report(name, scorefn):
        t = top1(rows, scorefn)
        pos = [(r, s, tid) for r, s, tid in t if r["relevant"]]
        neg = [(r, s, tid) for r, s, tid in t if not r["relevant"] and r["category"] in ("TROPE_ONLY", "TROPE_CHAIN_TRAP")]
        hit1 = np.mean([tid in r["relevant"] for r, s, tid in pos])
        auc = roc_auc_score([1] * len(pos) + [0] * len(neg), [s for _, s, _ in pos] + [s for _, s, _ in neg])
        print("%-34s hit@1=%.3f  AUC(overlap vs trope-only)=%.3f" % (name, hit1, auc))
        return t

    idx = {r["qid"]: k for k, r in enumerate(rows)}
    for j, f in enumerate(FEATS):
        report("single feature: " + f, lambda r, j=j: r["X"][:, j])
    report("fixed weights (design hypothesis)", lambda r: 0.40 * r["X"][:, 3] + 0.30 * np.minimum(1, r["X"][:, 1])
           + 0.20 * r["X"][:, 2] + 0.10 * r["X"][:, 4])
    t = report("LOQO-CV logistic combination", lambda r: cv_scores[idx[r["qid"]]])

    full = fit(rows, C=a.C)
    print("\nfull-fit coefficients (standardised):")
    for f, c in zip(FEATS, full["coef"]):
        print("  %-24s %+.2f" % (f, c))
    neg_scores = sorted([s for r, s, _ in t if not r["relevant"]], reverse=True)
    pos_scores = sorted([s for r, s, _ in t if r["relevant"] and r["category"] != "EXACT"])
    print("\nCV top-1 score, negatives (top 8):", [round(x, 2) for x in neg_scores[:8]])
    print("CV top-1 score, non-exact positives (lowest 8):", [round(x, 2) for x in pos_scores[:8]])
    # Tier thresholds are a CONSERVATIVE DESIGN CHOICE informed by the CV score distribution above:
    # the highest-scoring non-overlap pitch (an unrelated chess story vs. the maths-olympiad card) reaches ~0.64
    # and the lowest genuine partial overlap is ~0.68, so the gap is too thin to place High inside it.
    t_high, t_med = 0.80, 0.30
    print("tier thresholds (fixed by design): High>=%.2f  Medium>=%.2f" % (t_high, t_med))
    if a.write:
        out = {"tiers": {"high": t_high, "medium": t_med}, "features": FEATS, "mu": full["mu"].tolist(), "sd": full["sd"].tolist(), "coef": full["coef"].tolist(),
               "intercept": full["intercept"], "C": a.C, "fit_on": [str(Path(f).name) for f in files], "n_dev_queries": len(rows)}
        (ROOT / "storydna" / "calibration.json").write_text(json.dumps(out, indent=2))
        print("wrote storydna/calibration.json")


if __name__ == "__main__":
    main()
