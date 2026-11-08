#!/usr/bin/env python3
"""Collect every round's metrics.json into one CSV (no hand editing)."""
import csv, json
from pathlib import Path
R = Path(__file__).resolve().parent.parent / "raw_outputs"
keys = ["round", "n_queries", "hit_at_1", "plain_tfidf_hit_at_1", "top1_High_rate_EXACT", "top1_High_rate_PARAPHRASE", "top1_High_rate_PARTIAL",
        "trope_only_n", "trope_only_false_positive_rate_High", "trope_only_flagged_Medium_or_High_rate",
        "unrelated_n", "unrelated_false_positive_rate_High", "unrelated_flagged_Medium_or_High_rate",
        "auc_review_score_overlap_vs_trope", "auc_plain_cosine_overlap_vs_trope", "reports_failing_validation", "median_latency_ms"]
rows = [json.loads(p.read_text()) for p in sorted(R.glob("*/metrics.json"))]
with open(R / "evaluation_summary_all_rounds.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(keys)
    for m in rows:
        w.writerow([round(m[k], 3) if isinstance(m.get(k), float) else m.get(k, "") for k in keys])
for m in rows:
    print(m["round"], {k: (round(m[k], 2) if isinstance(m.get(k), float) else m.get(k)) for k in keys[1:11]})
