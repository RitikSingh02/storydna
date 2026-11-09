#!/usr/bin/env python3
"""Run the labelled benchmark and save every raw report.

Usage: python run_eval.py --round round1_apriori [--catalogue data/catalogue.json] [--queries data/benchmark/queries.json]

Writes raw_outputs/<round>/:  one JSON per query, test_case_manifest.csv, evaluation_results.csv,
metrics.json, tier_distribution.csv. Nothing is edited by hand.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from storydna.catalogue import load_catalogue  # noqa: E402
from storydna.matcher import StoryIndex  # noqa: E402
from storydna.report import review_pitch  # noqa: E402


def build_cases(cards, qfile):
    spec = json.loads(Path(qfile).read_text())
    by_id = {c.story_id: c for c in cards}
    cases = []
    for sid in spec.get("exact_ids", []):
        t = re.sub(r"[^\w\s]", "", by_id[sid].synopsis.lower())
        cases.append({"qid": "E_" + sid, "category": "EXACT", "relevant": [sid], "expected": ["High"],
                      "text": re.sub(r"\s+", " ", t)})
    cases += spec["queries"]
    return cases


def metrics(rows):
    pos = [r for r in rows if r["relevant"]]
    neg = [r for r in rows if not r["relevant"]]
    out = {"n_queries": len(rows), "n_with_relevant": len(pos), "n_without_relevant": len(neg)}
    out["hit_at_1"] = sum(r["rank_of_relevant"] == 1 for r in pos) / len(pos)
    out["recall_at_5"] = sum(r["rank_of_relevant"] is not None and r["rank_of_relevant"] <= 5 for r in pos) / len(pos)
    out["mrr"] = float(np.mean([1 / r["rank_of_relevant"] if r["rank_of_relevant"] else 0 for r in pos]))
    out["plain_tfidf_hit_at_1"] = sum(r["plain_rank_of_relevant"] == 1 for r in pos) / len(pos)
    out["plain_tfidf_mrr"] = float(np.mean([1 / r["plain_rank_of_relevant"] if r["plain_rank_of_relevant"] else 0 for r in pos]))
    for cat in ("EXACT", "PARAPHRASE", "PARTIAL"):
        sub = [r for r in pos if r["category"] == cat]
        if sub:
            out["top1_High_rate_" + cat] = sum(r["top1_tier"] == "High" for r in sub) / len(sub)
            out["top1_tier_in_expected_" + cat] = sum(r["tier_ok"] for r in sub) / len(sub)
    trope = [r for r in neg if r["category"] in ("TROPE_ONLY", "TROPE_CHAIN_TRAP")]
    unrel = [r for r in neg if r["category"] == "UNRELATED"]
    out["trope_only_n"] = len(trope)
    out["trope_only_false_positive_rate_High"] = sum(r["any_high"] for r in trope) / len(trope)
    out["trope_only_flagged_Medium_or_High_rate"] = sum(r["top1_tier"] in ("High", "Medium") for r in trope) / len(trope)
    out["unrelated_n"] = len(unrel)
    out["unrelated_false_positive_rate_High"] = sum(r["any_high"] for r in unrel) / len(unrel) if unrel else None
    out["unrelated_flagged_Medium_or_High_rate"] = sum(r["top1_tier"] in ("High", "Medium") for r in unrel) / len(unrel) if unrel else None
    # High-tier precision: of queries whose top-1 is High, how many had the right story on top
    high_top = [r for r in rows if r["top1_tier"] == "High"]
    out["high_flag_precision_top1"] = (sum(r["rank_of_relevant"] == 1 for r in high_top) / len(high_top)) if high_top else None
    out["n_top1_High"] = len(high_top)
    # Can the *score* separate genuine overlap from trope-only? (AUC on top-1 score)
    y = [1] * len(pos) + [0] * len(trope)
    out["auc_review_score_overlap_vs_trope"] = float(roc_auc_score(y, [r["top1_score"] for r in pos] + [r["top1_score"] for r in trope]))
    out["auc_plain_cosine_overlap_vs_trope"] = float(roc_auc_score(y, [r["top1_plain"] for r in pos] + [r["top1_plain"] for r in trope]))
    # evidence validity: every matched beat must exist verbatim in the sources (checked by validate_report)
    out["reports_failing_validation"] = sum(not r["valid"] for r in rows)
    out["median_latency_ms"] = float(np.median([r["latency_ms"] for r in rows]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True)
    ap.add_argument("--catalogue", default=str(ROOT / "data/catalogue.json"))
    ap.add_argument("--queries", default=str(ROOT / "data/benchmark/queries.json"))
    a = ap.parse_args()

    cards = load_catalogue(a.catalogue)
    ix = StoryIndex(cards)
    cases = build_cases(cards, a.queries)
    out = ROOT / "raw_outputs" / a.round
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for k, case in enumerate(cases, start=1):
        t0 = time.perf_counter()
        rep = review_pitch(ix, case["text"], query_id=case["qid"], title="%s [%s]" % (case["qid"], case["category"]),
                           top_k=5, run_label=a.round, suggest=False)
        lat = (time.perf_counter() - t0) * 1000
        rep["benchmark_label"] = {"category": case["category"], "relevant": case["relevant"], "expected_tiers": case["expected"]}
        (out / ("run_%03d_%s.json" % (k, case["qid"]))).write_text(json.dumps(rep, indent=2))
        # full (unfiltered) ranking for rank-of-relevant even when outside top-5
        q, _top, allr, extra = ix.score(case["text"], top_k=5)
        ids_ranked = [cards[r["idx"]].story_id for r in allr]
        plain_ranked = [cards[i].story_id for i in extra["plain_order"]]
        rel = case["relevant"]
        rank = next((i + 1 for i, s in enumerate(ids_ranked) if s in rel), None) if rel else None
        prank = next((i + 1 for i, s in enumerate(plain_ranked) if s in rel), None) if rel else None
        top = rep["top_candidates"][0]
        rows.append({
            "qid": case["qid"], "category": case["category"], "relevant": rel, "expected": case["expected"],
            "top1_id": top["candidate_id"], "top1_title": top["candidate_title"], "top1_tier": top["review_priority"],
            "top1_score": top["retrieval_score"], "top1_plain": top["components"]["plain_tfidf_cosine"],
            "rank_of_relevant": rank, "plain_rank_of_relevant": prank,
            "any_high": any(c["review_priority"] == "High" for c in rep["top_candidates"]),
            "tier_ok": top["review_priority"] in case["expected"],
            "valid": rep["validation"]["ok"], "latency_ms": round(lat, 1),
            "matched_beats_top1": len(top["matched_plot_beats"]),
            "ordered": top["components"]["ordered_event_overlap"], "lex": top["components"]["lexical_cosine"],
            "rare": top["components"]["rare_detail_overlap"],
        })
    with open(out / "evaluation_results.csv", "w", newline="") as f:
        w = csv.writer(f)
        keys = list(rows[0].keys())
        w.writerow(keys)
        for r in rows:
            w.writerow([";".join(v) if isinstance(v, list) else v for v in (r[k] for k in keys)])
    with open(out / "test_case_manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["qid", "category", "relevant_ids", "expected_tiers", "n_words"])
        for c in cases:
            w.writerow([c["qid"], c["category"], ";".join(c["relevant"]), ";".join(c["expected"]), len(c["text"].split())])
    m = metrics(rows)
    m["round"] = a.round
    (out / "metrics.json").write_text(json.dumps(m, indent=2))
    print(json.dumps(m, indent=2))
    print("\nPer-query top-1 (tier ok? ->):")
    for r in rows:
        flag = "ok " if r["tier_ok"] else "BAD"
        print("%-8s %-16s rel=%-6s top1=%s %-6s sc=%.2f ord=%.2f lex=%.2f rare=%.2f relrank=%s plainrank=%s %s" % (
            r["qid"], r["category"], ",".join(r["relevant"]) or "-", r["top1_id"], r["top1_tier"], r["top1_score"],
            r["ordered"], r["lex"], r["rare"], r["rank_of_relevant"], r["plain_rank_of_relevant"], flag))


if __name__ == "__main__":
    main()
